from django.shortcuts import render

def index(request):
    context = {}
    if request.method == 'POST':
        name = request.POST.get('name', '')
        context['name'] = name
    return render(request, 'hello_app/index.html', context)