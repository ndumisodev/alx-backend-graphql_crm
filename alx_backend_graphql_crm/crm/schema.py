import graphene
from graphene_django import DjangoObjectType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from .models import Customer, Product, Order
from django.utils import timezone

# ----------------
# GraphQL Types
# ----------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer


class ProductType(DjangoObjectType):
    class Meta:
        model = Product


class OrderType(DjangoObjectType):
    class Meta:
        model = Order


# ----------------
# Input Types
# ----------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime(required=False)


# ----------------
# Mutations
# ----------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        try:
            if Customer.objects.filter(email=input.email).exists():
                return CreateCustomer(errors=["Email already exists"])

            customer = Customer(
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            customer.full_clean()
            customer.save()

            return CreateCustomer(
                customer=customer,
                message="Customer created successfully",
                errors=[]
            )
        except ValidationError as e:
            return CreateCustomer(errors=e.messages)


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, input):
        created_customers = []
        errors = []

        for cust_data in input:
            try:
                if Customer.objects.filter(email=cust_data.email).exists():
                    errors.append(f"{cust_data.email}: Email already exists")
                    continue

                customer = Customer(
                    name=cust_data.name,
                    email=cust_data.email,
                    phone=cust_data.phone
                )
                customer.full_clean()
                customer.save()
                created_customers.append(customer)
            except ValidationError as e:
                errors.append(f"{cust_data.email}: {', '.join(e.messages)}")

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        try:
            if input.price <= 0:
                return CreateProduct(errors=["Price must be positive"])
            if input.stock is not None and input.stock < 0:
                return CreateProduct(errors=["Stock cannot be negative"])

            product = Product(
                name=input.name,
                price=input.price,
                stock=input.stock or 0
            )
            product.full_clean()
            product.save()
            return CreateProduct(product=product, errors=[])
        except ValidationError as e:
            return CreateProduct(errors=e.messages)


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        try:
            try:
                customer = Customer.objects.get(pk=input.customer_id)
            except ObjectDoesNotExist:
                return CreateOrder(errors=["Invalid customer ID"])

            products = Product.objects.filter(id__in=input.product_ids)
            if not products.exists():
                return CreateOrder(errors=["No valid products found"])
            if products.count() != len(input.product_ids):
                return CreateOrder(errors=["One or more product IDs are invalid"])

            total = sum([p.price for p in products])

            order = Order(
                customer=customer,
                total_amount=total,
                order_date=input.order_date or timezone.now()
            )
            order.save()
            order.products.set(products)

            return CreateOrder(order=order, errors=[])
        except ValidationError as e:
            return CreateOrder(errors=e.messages)


# ----------------
# Query & Mutation Root
# ----------------
class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)
    all_products = graphene.List(ProductType)
    all_orders = graphene.List(OrderType)

    def resolve_all_customers(self, info):
        return Customer.objects.all()

    def resolve_all_products(self, info):
        return Product.objects.all()

    def resolve_all_orders(self, info):
        return Order.objects.all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
