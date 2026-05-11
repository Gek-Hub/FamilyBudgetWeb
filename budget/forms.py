from django import forms
from django.utils import timezone
from .models import FamilyMember, Category, Wallet, BudgetLimit, Transaction

class FamilyRegisterForm(forms.Form):
    family_name = forms.CharField(label="Название семьи", max_length=120)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput, min_length=4)
    admin_name = forms.CharField(label="Ваше имя", max_length=150)
    admin_email = forms.EmailField(label="Ваш email")

class FamilyLoginForm(forms.Form):
    family_name = forms.CharField(label="Название семьи", max_length=120)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

class CurrentMemberForm(forms.Form):
    member = forms.ModelChoiceField(label="Кто сейчас пользуется приложением", queryset=FamilyMember.objects.none())

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields["member"].queryset = FamilyMember.objects.filter(family=family).order_by("full_name")

class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = FamilyMember
        fields = ["full_name", "email", "role"]
        labels = {
            "full_name": "Имя члена семьи",
            "email": "Email",
            "role": "Роль",
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "type"]
        labels = {
            "name": "Название категории",
            "type": "Тип",
        }

class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = ["name", "currency", "exchange_rate_to_rub"]
        labels = {
            "name": "Название счета",
            "currency": "Валюта",
            "exchange_rate_to_rub": "Курс к рублю",
        }

class BudgetLimitForm(forms.ModelForm):
    class Meta:
        model = BudgetLimit
        fields = ["category", "monthly_limit"]
        labels = {
            "category": "Категория расходов",
            "monthly_limit": "Лимит на месяц",
        }

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields["category"].queryset = Category.objects.filter(family=family, type="Расход").order_by("name")

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["type", "category", "wallet", "family_member", "amount", "date", "comment"]
        widgets = {
            "date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date"
                }
            ),
            "comment": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "type": "Тип операции",
            "category": "Категория",
            "wallet": "Счет",
            "family_member": "Член семьи",
            "amount": "Сумма",
            "date": "Дата",
            "comment": "Комментарий",
        }

    def __init__(self, *args, family=None, current_member_id=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["date"].input_formats = ["%Y-%m-%d"]

        if family:
            categories = Category.objects.filter(family=family).order_by("type", "name")
            wallets = Wallet.objects.filter(family=family).order_by("name")
            members = FamilyMember.objects.filter(family=family).order_by("full_name")

            self.fields["category"].queryset = categories
            self.fields["wallet"].queryset = wallets
            self.fields["family_member"].queryset = members

            # Значения по умолчанию только при открытии пустой формы, не при POST-запросе
            if not self.is_bound:
                today = timezone.now().date().strftime("%Y-%m-%d")

                self.fields["type"].initial = "Расход"
                self.fields["date"].initial = today
                self.fields["date"].widget.attrs["value"] = today

                food_category = Category.objects.filter(
                    family=family,
                    name="Еда",
                    type="Расход"
                ).first()

                if food_category:
                    self.fields["category"].initial = food_category.id

                card_wallet = Wallet.objects.filter(
                    family=family,
                    name="Карта RUB"
                ).first()

                if card_wallet:
                    self.fields["wallet"].initial = card_wallet.id

                if current_member_id:
                    self.fields["family_member"].initial = current_member_id
