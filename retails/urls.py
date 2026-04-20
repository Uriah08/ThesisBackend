from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.CreateRetailShopView.as_view(), name="create-retail-store"),
    path('list/<int:farm_id>/', views.ListRetailShopsView.as_view(), name="list-retail-shops"),
    path('retrieve/<int:shop_id>/', views.RetrieveRetailShopView.as_view(), name="retrieve-retail-shop"),
    path('update/<int:shop_id>/', views.UpdateRetailShopView.as_view(), name="update-retail-shop"),
    path('delete/<int:shop_id>/', views.DeleteRetailShopView.as_view(), name="delete-retail-shop"),
]