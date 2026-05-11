from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from budget.models import FamilyAccount, FamilyMember, Category, Wallet, Transaction
from budget.views import create_default_data

class Command(BaseCommand):
    help = "Создает демонстрационные семьи"

    def handle(self, *args, **options):
        self.create_family_with_data("Поттеровы", [
            ("Гарри Поттер","harry@potter.family","Администратор"),
            ("Джинни Поттер","ginny@potter.family","Участник"),
            ("Джеймс Поттер","james@potter.family","Участник"),
        ], [
            ("Доход","Зарплата","Карта RUB","Гарри Поттер",85000,"Основной доход Гарри"),
            ("Расход","Еда","Карта RUB","Джинни Поттер",7400,"Продукты на неделю"),
            ("Расход","Транспорт","Карта RUB","Гарри Поттер",1450,"Проезд и такси"),
            ("Расход","Коммунальные услуги","Карта RUB","Джинни Поттер",6200,"Оплата коммунальных услуг"),
            ("Расход","Развлечения","Карта RUB","Джеймс Поттер",2800,"Кино и кафе"),
            ("Доход","Подработка","Карта RUB","Джинни Поттер",12000,"Дополнительный доход"),
            ("Расход","Здоровье","Наличные RUB","Гарри Поттер",3500,"Аптека"),
            ("Расход","Одежда","Карта RUB","Джинни Поттер",9100,"Покупка одежды"),
            ("Расход","Еда","Наличные RUB","Джеймс Поттер",1200,"Обед вне дома"),
            ("Доход","Подарки","Карта RUB","Джеймс Поттер",5000,"Подарок от родственников"),
        ])
        self.create_family_with_data("Ивановы", [
            ("Иван Иванов","ivan@ivanov.family","Администратор"),
            ("Мария Иванова","maria@ivanov.family","Участник"),
            ("Анна Иванова","anna@ivanov.family","Участник"),
        ], [
            ("Доход","Зарплата","Карта RUB","Иван Иванов",72000,"Зарплата Ивана"),
            ("Доход","Зарплата","Карта RUB","Мария Иванова",56000,"Зарплата Марии"),
            ("Расход","Еда","Карта RUB","Мария Иванова",11800,"Покупка продуктов"),
            ("Расход","Коммунальные услуги","Карта RUB","Иван Иванов",6900,"Кварплата"),
            ("Расход","Транспорт","Карта RUB","Иван Иванов",3270,"Проездной и бензин"),
            ("Расход","Развлечения","Наличные RUB","Анна Иванова",2400,"Кинотеатр"),
            ("Расход","Одежда","Карта RUB","Мария Иванова",7600,"Одежда для семьи"),
            ("Расход","Здоровье","Карта RUB","Иван Иванов",4100,"Лекарства"),
            ("Расход","Еда","Наличные RUB","Анна Иванова",950,"Кафе после учебы"),
            ("Доход","Подарки","Карта RUB","Анна Иванова",3000,"Подарок"),
        ])
        self.create_family_with_data("Османовы", [
            ("Газибег Османов","gazibeg@osmanov.family","Администратор"),
            ("Аминат Османова","aminat@osmanov.family","Участник"),
            ("Магомед Османов","magomed@osmanov.family","Участник"),
        ], [
            ("Доход","Зарплата","Карта RUB","Газибег Османов",90000,"Основная зарплата"),
            ("Доход","Подработка","Карта RUB","Газибег Османов",18000,"Дополнительный проект"),
            ("Расход","Еда","Карта RUB","Аминат Османова",12750,"Продукты для дома"),
            ("Расход","Коммунальные услуги","Карта RUB","Газибег Османов",7200,"Коммунальные платежи"),
            ("Расход","Транспорт","Наличные RUB","Магомед Османов",1800,"Транспорт за неделю"),
            ("Расход","Развлечения","Карта RUB","Магомед Османов",3500,"Отдых с друзьями"),
            ("Расход","Одежда","Карта RUB","Аминат Османова",10400,"Покупка одежды"),
            ("Расход","Здоровье","Карта RUB","Газибег Османов",5200,"Медицинские расходы"),
            ("Расход","Еда","Наличные RUB","Магомед Османов",1600,"Кафе"),
            ("Доход","Подарки","Карта RUB","Аминат Османова",7000,"Подарок от родственников"),
        ])
        self.stdout.write(self.style.SUCCESS("Демо-семьи готовы. Пароль: 1234"))

    def create_family_with_data(self, family_name, members, transactions):
        family = FamilyAccount.objects.filter(family_name=family_name).first()
        if not family:
            family = FamilyAccount(family_name=family_name)
            family.set_password("1234")
            family.save()
            create_default_data(family)
        member_map = {}
        for full_name, email, role in members:
            member, _ = FamilyMember.objects.get_or_create(family=family, full_name=full_name, defaults={"email":email, "role":role})
            member_map[full_name] = member
        for i, (type_, cat_name, wallet_name, member_name, amount, comment) in enumerate(transactions):
            if Transaction.objects.filter(family=family, comment=comment).exists():
                continue
            category = Category.objects.get(family=family, name=cat_name, type=type_)
            wallet = Wallet.objects.get(family=family, name=wallet_name)
            Transaction.objects.create(family=family, type=type_, category=category, wallet=wallet, family_member=member_map[member_name], amount=Decimal(str(amount)), amount_rub=Decimal("0"), date=timezone.now().date()-timezone.timedelta(days=i), comment=comment, is_synced=False)
