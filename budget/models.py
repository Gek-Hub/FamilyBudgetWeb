from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from .security import encrypt_text, decrypt_text

class FamilyAccount(models.Model):
    family_name = models.CharField("Название семьи", max_length=120, unique=True)
    password = models.CharField("Хеш пароля", max_length=255)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.family_name

class FamilyMember(models.Model):
    ROLE_CHOICES = [("Администратор", "Администратор"), ("Участник", "Участник")]
    family = models.ForeignKey(FamilyAccount, on_delete=models.CASCADE, related_name="members")
    full_name = models.CharField("ФИО", max_length=150)
    email = models.TextField("Email")
    role = models.CharField("Роль", max_length=30, choices=ROLE_CHOICES, default="Участник")

    @property
    def email_for_display(self):
        return decrypt_text(self.email)

    def save(self, *args, **kwargs):
        if self.email and not self.email.startswith("enc:"):
            self.email = encrypt_text(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name

class Category(models.Model):
    TYPE_CHOICES = [("Доход", "Доход"), ("Расход", "Расход")]
    family = models.ForeignKey(FamilyAccount, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField("Название", max_length=100)
    type = models.CharField("Тип", max_length=20, choices=TYPE_CHOICES, default="Расход")

    class Meta:
        unique_together = ("family", "name", "type")

    def __str__(self):
        return f"{self.name} ({self.type})"

class Wallet(models.Model):
    family = models.ForeignKey(FamilyAccount, on_delete=models.CASCADE, related_name="wallets")
    name = models.CharField("Название", max_length=100)
    currency = models.CharField("Валюта", max_length=10, default="RUB")
    exchange_rate_to_rub = models.DecimalField("Курс к рублю", max_digits=12, decimal_places=2, default=1)

    def __str__(self):
        return f"{self.name} ({self.currency})"

class BudgetLimit(models.Model):
    family = models.ForeignKey(FamilyAccount, on_delete=models.CASCADE, related_name="limits")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="limits")
    monthly_limit = models.DecimalField("Лимит на месяц", max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("family", "category")

class Transaction(models.Model):
    TYPE_CHOICES = [("Доход", "Доход"), ("Расход", "Расход")]
    family = models.ForeignKey(FamilyAccount, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField("Тип", max_length=20, choices=TYPE_CHOICES, default="Расход")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    family_member = models.ForeignKey(FamilyMember, on_delete=models.PROTECT, related_name="transactions")
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2)
    amount_rub = models.DecimalField("Сумма в рублях", max_digits=12, decimal_places=2)
    date = models.DateField("Дата")
    comment = models.TextField("Комментарий", blank=True)
    is_synced = models.BooleanField("Синхронизировано", default=False)

    class Meta:
        ordering = ["-date", "-id"]

    def save(self, *args, **kwargs):
        self.amount_rub = self.amount * self.wallet.exchange_rate_to_rub
        super().save(*args, **kwargs)
