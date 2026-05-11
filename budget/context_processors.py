def current_account(request):
    return {
        "current_family_name": request.session.get("family_name", ""),
        "current_member_name": request.session.get("member_name", ""),
        "current_member_role": request.session.get("member_role", ""),
    }
