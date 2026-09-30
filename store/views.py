from django.http import HttpResponse


def product_page(request):
    return HttpResponse(f"Welcome {request.user.username}! Product page coming in Step 2.2.")