from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .models import RetailShop
from .serializers import RetailShopSerializer
from farms.models import FarmModel


class CreateRetailShopView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RetailShopSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            farm_id = request.data.get("farm")
            if not farm_id:
                return Response({"farm": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                farm = FarmModel.objects.get(id=farm_id)
            except FarmModel.DoesNotExist:
                return Response({"farm": "Farm not found."}, status=status.HTTP_400_BAD_REQUEST)

            if farm.owner != request.user:
                return Response({"detail": "Only the farm owner can add a retail shop."},
                                status=status.HTTP_403_FORBIDDEN)

            shop = serializer.save(farm=farm)
            response_serializer = RetailShopSerializer(shop, context={"request": request})
            return Response({"detail": "Retail shop created successfully.",
                             "retail_shop": response_serializer.data},
                            status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListRetailShopsView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        try:
            farm = FarmModel.objects.get(id=farm_id)
        except FarmModel.DoesNotExist:
            return Response({"farm": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

        if not (farm.owner == request.user or request.user in farm.members.all()):
            return Response({"detail": "You are not allowed to view retail shops for this farm."},
                            status=status.HTTP_403_FORBIDDEN)

        shops = RetailShop.objects.filter(farm=farm)
        serializer = RetailShopSerializer(shops, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveRetailShopView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, shop_id):
        try:
            shop = RetailShop.objects.get(id=shop_id)
        except RetailShop.DoesNotExist:
            return Response({"detail": "Retail shop not found."}, status=status.HTTP_404_NOT_FOUND)

        farm = shop.farm
        if not (farm.owner == request.user or request.user in farm.members.all()):
            return Response({"detail": "You are not allowed to view this retail shop."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = RetailShopSerializer(shop, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateRetailShopView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, shop_id):
        try:
            shop = RetailShop.objects.get(id=shop_id)
        except RetailShop.DoesNotExist:
            return Response({"detail": "Retail shop not found."}, status=status.HTTP_404_NOT_FOUND)

        if shop.farm.owner != request.user:
            return Response({"detail": "Only the farm owner can update this retail shop."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = RetailShopSerializer(shop, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Retail shop updated successfully.", "retail_shop": serializer.data},
                            status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteRetailShopView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, shop_id):
        try:
            shop = RetailShop.objects.get(id=shop_id)
        except RetailShop.DoesNotExist:
            return Response({"detail": "Retail shop not found."}, status=status.HTTP_404_NOT_FOUND)

        if shop.farm.owner != request.user:
            return Response({"detail": "Only the farm owner can delete this retail shop."},
                            status=status.HTTP_403_FORBIDDEN)

        shop.delete()
        return Response({"detail": "Retail shop deleted successfully."}, status=status.HTTP_204_NO_CONTENT)