from django.contrib import admin
from .models import FamilyAccount, FamilyMember, Category, Wallet, BudgetLimit, Transaction

admin.site.register(FamilyAccount)
admin.site.register(FamilyMember)
admin.site.register(Category)
admin.site.register(Wallet)
admin.site.register(BudgetLimit)
admin.site.register(Transaction)
