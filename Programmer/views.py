from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from Client.models import Service, PortfolioItem, Category
from .forms import ServiceForm, PortfolioForm


def developer_required(view_func):

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('client:login')
        if not request.user.is_developer:
            raise PermissionDenied('Faqat dasturchilar uchun.')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper



class ServiceCreateView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        return render(request, 'programmer/service_form.html', {
            'form': ServiceForm(),
            'title': 'Yangi xizmat qo\'shish',
            'action': 'create',
        })

    def post(self, request):
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.developer = request.user
            service.save()
            messages.success(request, f'"{service.title}" xizmati yaratildi.')
            return redirect('programmer:service_list')
        return render(request, 'programmer/service_form.html', {
            'form': form, 'title': 'Yangi xizmat', 'action': 'create'
        })


class ServiceListView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        services = Service.objects.filter(developer=request.user).order_by('-created_at')
        paginator = Paginator(services, 20)
        page_obj  = paginator.get_page(request.GET.get('page'))
        return render(request, 'programmer/service_list.html', {'page_obj': page_obj})


class ServiceUpdateView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def _get_service(self, request, pk):
        service = get_object_or_404(Service, pk=pk, developer=request.user)
        if service.has_active_orders():
            messages.error(request, 'Faol buyurtmalari bor xizmatni tahrirlash mumkin emas.')
            return None
        return service

    def get(self, request, pk):
        service = self._get_service(request, pk)
        if service is None:
            return redirect('programmer:service_list')
        return render(request, 'programmer/service_form.html', {
            'form': ServiceForm(instance=service),
            'title': 'Xizmatni tahrirlash',
            'action': 'update',
            'service': service,
        })

    def post(self, request, pk):
        service = self._get_service(request, pk)
        if service is None:
            return redirect('programmer:service_list')
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Xizmat yangilandi.')
            return redirect('programmer:service_list')
        return render(request, 'programmer/service_form.html', {
            'form': form, 'title': 'Tahrirlash', 'service': service
        })


class ServiceDeleteView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        service = get_object_or_404(Service, pk=pk, developer=request.user)
        return render(request, 'programmer/service_confirm_delete.html', {'service': service})

    def post(self, request, pk):
        service = get_object_or_404(Service, pk=pk, developer=request.user)
        if service.has_active_orders():
            messages.error(request, 'Faol buyurtmalari bor xizmatni o\'chirish mumkin emas.')
            return redirect('programmer:service_list')
        title = service.title
        service.delete()
        messages.success(request, f'"{title}" xizmati o\'chirildi.')
        return redirect('programmer:service_list')



class PortfolioListView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        items = PortfolioItem.objects.filter(developer=request.user).order_by('order', '-created_at')
        return render(request, 'programmer/portfolio_list.html', {'items': items})


class PortfolioCreateView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        return render(request, 'programmer/portfolio_form.html', {
            'form': PortfolioForm(), 'title': 'Portfolio qo\'shish'
        })

    def post(self, request):
        form = PortfolioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.developer = request.user
            item.save()
            messages.success(request, 'Portfolio element qo\'shildi.')
            return redirect('programmer:portfolio_list')
        return render(request, 'programmer/portfolio_form.html', {'form': form, 'title': 'Portfolio qo\'shish'})


class PortfolioUpdateView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        item = get_object_or_404(PortfolioItem, pk=pk, developer=request.user)
        return render(request, 'programmer/portfolio_form.html', {
            'form': PortfolioForm(instance=item),
            'title': 'Portfolio tahrirlash',
            'item': item,
        })

    def post(self, request, pk):
        item = get_object_or_404(PortfolioItem, pk=pk, developer=request.user)
        form = PortfolioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Portfolio yangilandi.')
            return redirect('programmer:portfolio_list')
        return render(request, 'programmer/portfolio_form.html', {'form': form, 'title': 'Tahrirlash', 'item': item})


class PortfolioDeleteView(View):
    @method_decorator(developer_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, pk):
        item = get_object_or_404(PortfolioItem, pk=pk, developer=request.user)
        item.delete()
        messages.success(request, 'Portfolio element o\'chirildi.')
        return redirect('programmer:portfolio_list')