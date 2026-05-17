from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .deepseek_service import parse_voice_command, normalize_amount
from .models import FamilyAccount, FamilyMember, Category, Wallet, BudgetLimit, Transaction
from .forms import FamilyRegisterForm, FamilyLoginForm, CurrentMemberForm, FamilyMemberForm, CategoryForm, WalletForm, BudgetLimitForm, TransactionForm

def get_current_family(request):
    family_id = request.session.get("family_id")
    return FamilyAccount.objects.filter(id=family_id).first() if family_id else None

def login_required_family(view_func):
    def wrapper(request, *args, **kwargs):
        if not get_current_family(request):
            return redirect("login_family")
        return view_func(request, *args, **kwargs)
    return wrapper

def set_current_member_session(request, member):
    request.session["member_id"] = member.id
    request.session["member_name"] = member.full_name
    request.session["member_role"] = member.role

def login_family(request):
    if get_current_family(request):
        return redirect("dashboard")
    form = FamilyLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        family = FamilyAccount.objects.filter(family_name__iexact=form.cleaned_data["family_name"]).first()
        if not family or not family.check_password(form.cleaned_data["password"]):
            messages.error(request, "Семья не найдена или пароль указан неверно.")
        else:
            request.session["family_id"] = family.id
            request.session["family_name"] = family.family_name
            member = family.members.order_by("id").first()
            if member:
                set_current_member_session(request, member)
            return redirect("dashboard")
    return render(request, "budget/login.html", {"form": form})

def register_family(request):
    if get_current_family(request):
        return redirect("dashboard")
    form = FamilyRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if FamilyAccount.objects.filter(family_name__iexact=form.cleaned_data["family_name"]).exists():
            messages.error(request, "Такая семья уже существует.")
        else:
            family = FamilyAccount(family_name=form.cleaned_data["family_name"])
            family.set_password(form.cleaned_data["password"])
            family.save()
            create_default_data(family)
            admin = FamilyMember.objects.create(family=family, full_name=form.cleaned_data["admin_name"], email=form.cleaned_data["admin_email"], role="Администратор")
            request.session["family_id"] = family.id
            request.session["family_name"] = family.family_name
            set_current_member_session(request, admin)
            return redirect("dashboard")
    return render(request, "budget/register.html", {"form": form})

def logout_family(request):
    request.session.flush()
    return redirect("login_family")

@login_required_family
def dashboard(request):
    family = get_current_family(request)
    qs = Transaction.objects.filter(family=family)
    income = qs.filter(type="Доход").aggregate(total=Sum("amount_rub"))["total"] or Decimal("0")
    expense = qs.filter(type="Расход").aggregate(total=Sum("amount_rub"))["total"] or Decimal("0")
    return render(request, "budget/dashboard.html", {"income": income, "expense": expense, "balance": income-expense, "last_transactions": qs[:5]})

@login_required_family
def account(request):
    family = get_current_family(request)
    form = CurrentMemberForm(request.POST or None, family=family)
    if request.method == "POST" and form.is_valid():
        set_current_member_session(request, form.cleaned_data["member"])
        return redirect("account")
    return render(request, "budget/account.html", {"form": form})

@login_required_family
def transactions(request):
    return render(request, "budget/transactions.html", {"items": Transaction.objects.filter(family=get_current_family(request))})

@login_required_family
def add_transaction(request):
    family = get_current_family(request)
    form = TransactionForm(request.POST or None, family=family, current_member_id=request.session.get("member_id"))
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.family = family
        item.save()
        return redirect("transactions")
    return render(request, "budget/form_page.html", {"form": form, "title": "Добавление операции"})


@login_required_family
def edit_transaction(request, pk):
    family = get_current_family(request)
    transaction = get_object_or_404(Transaction, id=pk, family=family)

    form = TransactionForm(
        request.POST or None,
        instance=transaction,
        family=family,
        current_member_id=request.session.get("member_id")
    )

    if request.method == "POST" and form.is_valid():
        edited_transaction = form.save(commit=False)
        edited_transaction.family = family
        edited_transaction.save()
        messages.success(request, "Операция обновлена.")
        return redirect("dashboard")

    return render(request, "budget/form_page.html", {
        "form": form,
        "title": "Редактирование операции"
    })

@login_required_family
def delete_transaction(request, pk):
    family = get_current_family(request)
    item = get_object_or_404(Transaction, id=pk, family=family)

    # Запоминаем страницу, с которой пришел пользователь
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"

    item.delete()
    messages.success(request, "Операция удалена.")

    return redirect(next_url)

@login_required_family
def family_members(request):
    family = get_current_family(request)
    form = FamilyMemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False); item.family = family; item.save()
        return redirect("family_members")
    return render(request, "budget/family.html", {"form": form, "items": FamilyMember.objects.filter(family=family)})

@login_required_family
def delete_member(request, pk):
    member = get_object_or_404(FamilyMember, id=pk, family=get_current_family(request))
    if member.id != request.session.get("member_id"):
        member.delete()
    return redirect("family_members")

@login_required_family
def categories(request):
    family = get_current_family(request)
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False); item.family = family; item.save()
        return redirect("categories")
    return render(request, "budget/categories.html", {"form": form, "items": Category.objects.filter(family=family).order_by("type","name")})

@login_required_family
def delete_category(request, pk):
    item = get_object_or_404(Category, id=pk, family=get_current_family(request))
    if not Transaction.objects.filter(category=item).exists():
        item.delete()
    return redirect("categories")

@login_required_family
def wallets(request):
    family = get_current_family(request)
    form = WalletForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False); item.family = family; item.save()
        return redirect("wallets")
    return render(request, "budget/wallets.html", {"form": form, "items": Wallet.objects.filter(family=family)})

@login_required_family
def delete_wallet(request, pk):
    item = get_object_or_404(Wallet, id=pk, family=get_current_family(request))
    if not Transaction.objects.filter(wallet=item).exists():
        item.delete()
    return redirect("wallets")

@login_required_family
def budget_limits(request):
    family = get_current_family(request)
    form = BudgetLimitForm(request.POST or None, family=family)
    if request.method == "POST" and form.is_valid():
        category = form.cleaned_data["category"]
        limit, _ = BudgetLimit.objects.get_or_create(family=family, category=category)
        limit.monthly_limit = form.cleaned_data["monthly_limit"]; limit.save()
        return redirect("budget_limits")
    current_month = timezone.now().date().replace(day=1)
    statuses = []
    for limit in BudgetLimit.objects.filter(family=family).select_related("category"):
        spent = Transaction.objects.filter(family=family, type="Расход", category=limit.category, date__gte=current_month).aggregate(total=Sum("amount_rub"))["total"] or Decimal("0")
        percent = float(spent / limit.monthly_limit * 100) if limit.monthly_limit else 0
        statuses.append({"category": limit.category.name, "limit": limit.monthly_limit, "spent": spent, "remaining": limit.monthly_limit-spent, "percent": min(percent,100), "is_over": spent > limit.monthly_limit})
    return render(request, "budget/budget.html", {"form": form, "statuses": statuses})

@login_required_family
def analytics(request):
    family = get_current_family(request)
    report_type = request.GET.get("report_type", "Расходы по категориям")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    qs = Transaction.objects.filter(family=family).select_related("category","family_member","wallet")
    if start_date: qs = qs.filter(date__gte=start_date)
    if end_date: qs = qs.filter(date__lte=end_date)
    operation_type = "Доход" if "Доходы" in report_type else "Расход"
    transactions = list(qs.filter(type=operation_type))
    total = sum((t.amount_rub for t in transactions), Decimal("0"))
    groups = {}
    for t in transactions:
        if "категориям" in report_type: key = t.category.name
        elif "членам семьи" in report_type: key = t.family_member.full_name
        else: key = f"{t.family_member.full_name} — {t.category.name}"
        groups.setdefault(key, {"name": key, "amount": Decimal("0"), "details": []})
        groups[key]["amount"] += t.amount_rub
        groups[key]["details"].append(t)
    result = []
    for group in groups.values():
        group["share"] = float(group["amount"] / total * 100) if total else 0
        result.append(group)
    result.sort(key=lambda x: x["amount"], reverse=True)
    return render(request, "budget/analytics.html", {"report_type": report_type, "start_date": start_date, "end_date": end_date, "total": total, "groups": result, "report_types": ["Расходы по категориям","Доходы по категориям","Расходы по членам семьи","Доходы по членам семьи","Расходы: член семьи и категория","Доходы: член семьи и категория"]})

def create_default_data(family):
    for name, type_ in [("Зарплата","Доход"),("Подработка","Доход"),("Подарки","Доход"),("Еда","Расход"),("Транспорт","Расход"),("Коммунальные услуги","Расход"),("Развлечения","Расход"),("Здоровье","Расход"),("Одежда","Расход")]:
        Category.objects.get_or_create(family=family, name=name, type=type_)
    for name, currency, rate in [("Наличные RUB","RUB",1),("Карта RUB","RUB",1),("Счет USD","USD",90),("Счет EUR","EUR",100)]:
        Wallet.objects.get_or_create(family=family, name=name, defaults={"currency":currency, "exchange_rate_to_rub":rate})




@csrf_exempt
@require_POST
def voice_command(request):
    family = get_current_family(request)

    if not family:
        return JsonResponse({"ok": False, "error": "Не выполнен вход в семью."}, status=403)

    command_text = ""

    if request.POST.get("text"):
        command_text = request.POST.get("text", "").strip()

    if not command_text:
        raw_body = request.body.decode("utf-8", errors="ignore").strip()

        if raw_body:
            try:
                body = json.loads(raw_body)
                command_text = (body.get("text") or "").strip()
            except Exception:
                command_text = raw_body.strip()

    if not command_text:
        return JsonResponse({
            "ok": False,
            "error": "Команда пустая. Введите, например: добавь спорт 2500 сегодня"
        }, status=400)

    try:
        categories = list(Category.objects.filter(family=family).order_by("type", "name").values_list("name", flat=True))
        wallets = list(Wallet.objects.filter(family=family).order_by("name").values_list("name", flat=True))
        members = list(FamilyMember.objects.filter(family=family).order_by("full_name").values_list("full_name", flat=True))

        parsed = parse_voice_command(
            command_text,
            category_names=categories,
            wallet_names=wallets,
            member_names=members
        )

        operation_type = parsed.get("type", "Расход")

        if operation_type not in ["Доход", "Расход"]:
            operation_type = "Расход"

        category_name = str(parsed.get("category", "Еда")).strip() or "Еда"
        amount = Decimal(normalize_amount(parsed.get("amount", 0)))

        if amount <= 0:
            return JsonResponse({
                "ok": False,
                "error": "Не удалось определить сумму операции. Пример: добавь спорт 2500 сегодня"
            }, status=400)

        date_raw = str(parsed.get("date", "today")).strip().lower()

        if date_raw in ["today", "сегодня", ""]:
            operation_date = timezone.now().date()
        else:
            operation_date = timezone.datetime.strptime(date_raw, "%Y-%m-%d").date()

        comment = parsed.get("comment", "") or f"Добавлено через AI-команду: {command_text}"

        # Сначала ищем категорию по точному имени
        category = Category.objects.filter(
            family=family,
            name__iexact=category_name,
            type=operation_type
        ).first()

        # Если тип не совпал, но такая категория есть в семье, используем ее и ее тип
        if not category:
            category = Category.objects.filter(
                family=family,
                name__iexact=category_name
            ).first()

            if category:
                operation_type = category.type

        # Если категории нет, создаем новую
        if not category:
            category = Category.objects.create(
                family=family,
                name=category_name,
                type=operation_type
            )

        wallet = Wallet.objects.filter(family=family, name="Карта RUB").first()

        if not wallet:
            wallet = Wallet.objects.filter(family=family).first()

        if not wallet:
            return JsonResponse({"ok": False, "error": "В семье не найден счет."}, status=400)

        member = FamilyMember.objects.filter(
            family=family,
            id=request.session.get("member_id")
        ).first()

        if not member:
            member = FamilyMember.objects.filter(family=family).first()

        if not member:
            return JsonResponse({"ok": False, "error": "В семье не найден участник."}, status=400)

        transaction = Transaction.objects.create(
            family=family,
            type=operation_type,
            category=category,
            wallet=wallet,
            family_member=member,
            amount=amount,
            amount_rub=Decimal("0"),
            date=operation_date,
            comment=comment,
            is_synced=False,
        )

        return JsonResponse({
            "ok": True,
            "message": "Операция успешно добавлена.",
            "transaction": {
                "type": transaction.type,
                "category": transaction.category.name,
                "wallet": transaction.wallet.name,
                "member": transaction.family_member.full_name,
                "amount": str(transaction.amount),
                "amount_rub": str(transaction.amount_rub),
                "date": str(transaction.date),
                "comment": transaction.comment,
            }
        })

    except Exception as ex:
        return JsonResponse({
            "ok": False,
            "error": f"Ошибка обработки команды: {ex}"
        }, status=400)




@login_required_family
def transaction_detail(request, pk):
    family = get_current_family(request)
    item = get_object_or_404(
        Transaction.objects.select_related("family", "category", "wallet", "family_member"),
        id=pk,
        family=family
    )
    return render(request, "budget/transaction_detail.html", {"item": item})


@login_required_family
def api_transactions(request):
    family = get_current_family(request)

    search = request.GET.get("search", "").strip()
    sort = request.GET.get("sort", "-date")
    page_number = request.GET.get("page", "1")
    per_page = request.GET.get("per_page", "5")

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 5

    if per_page not in [5, 10, 15]:
        per_page = 5

    sort_map = {
        "-date": "-date",
        "date": "date",
        "-amount": "-amount_rub",
        "amount": "amount_rub",
        "category": "category__name",
        "-category": "-category__name",
        "member": "family_member__full_name",
        "-member": "-family_member__full_name",
        "type": "type",
        "-type": "-type",
        "-id": "-id",
        "id": "id",
    }

    sort_field = sort_map.get(sort, "-date")

    qs = Transaction.objects.filter(family=family).select_related("category", "wallet", "family_member")

    if search:
        qs = qs.filter(
            Q(category__name__icontains=search) |
            Q(wallet__name__icontains=search) |
            Q(family_member__full_name__icontains=search) |
            Q(type__icontains=search) |
            Q(comment__icontains=search)
        )

    qs = qs.order_by(sort_field, "-id")

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_number)

    items = []
    for item in page_obj.object_list:
        items.append({
            "id": item.id,
            "type": item.type,
            "category": item.category.name,
            "wallet": item.wallet.name,
            "member": item.family_member.full_name,
            "amount": str(item.amount),
            "amount_rub": str(item.amount_rub),
            "date": item.date.strftime("%d.%m.%Y"),
            "comment": item.comment or "",
            "detail_url": reverse("transaction_detail", args=[item.id]),
            "edit_url": reverse("edit_transaction", args=[item.id]),
            "delete_url": reverse("delete_transaction", args=[item.id]) + "?next=" + reverse("transactions"),
        })

    return JsonResponse({
        "ok": True,
        "items": items,
        "pagination": {
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "total_items": paginator.count,
            "per_page": per_page,
        }
    })
