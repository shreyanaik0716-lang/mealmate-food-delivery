
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
import razorpay
from django.shortcuts import render, redirect

from mealmate import settings
from .models import Cart, Customer, Item, Restaurant


# Create your views here.
def index(request):
    return render(request, 'delivery/index.html')

def open_signup(request):
    return render(request, 'delivery/signup.html')

def open_signin(request):
    return render(request, 'delivery/signin.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        address = request.POST.get('address')

        try:
            Customer.objects.get(username = username)
            return HttpResponse("Duplicate username!")
        except:
            Customer.objects.create(
                username = username,
                password = password,
                email = email,
                mobile = mobile,
                address = address,
            )
    return render(request, 'delivery/signin.html')

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            customer = Customer.objects.get(
                username=username,
                password=password
            )

            if customer.username == 'admin':
                return render(request, 'delivery/admin_home.html')
            else:
                restaurantList = Restaurant.objects.all()
                return render(request, 'delivery/customer_home.html',{"restaurantList":restaurantList, "username": username})

        except Customer.DoesNotExist:
            return render(request, 'delivery/fail.html')

    return render(request, 'delivery/signin.html')

    
def open_add_restaurant(request):
    return render(request, 'delivery/add_restaurant.html')

def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture') # ✅ Corrected
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')

        try:
            Restaurant.objects.get(name = name)
            return HttpResponse("Duplicate restaurant!")
        except Restaurant.DoesNotExist:
            Restaurant.objects.create(
                name=name,
                picture=picture,
                cuisine=cuisine,
                rating=rating,
            )
    return render(request, 'delivery/admin_home.html')

def open_show_restaurant(request):
    restaurantList = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html',{"restaurantList" : restaurantList})

def open_update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    return render(request, 'delivery/update_restaurant.html', {"restaurant" : restaurant})

def update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')
        
        restaurant.name = name
        restaurant.picture = picture
        restaurant.cuisine = cuisine
        restaurant.rating = rating

        restaurant.save()

    restaurantList = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html',{"restaurantList" : restaurantList})

def delete_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    restaurant.delete()

    restaurantList = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html',{"restaurantList" : restaurantList})
    
def open_update_menu(request, restaurant_id):

    restaurant = Restaurant.objects.get(id=restaurant_id)

    itemList = restaurant.items.all()

    return render(
        request,
        'delivery/update_menu.html',
        {
            'itemList': itemList,
            'restaurant': restaurant
        }
    )


def update_menu(request, restaurant_id):

    restaurant = Restaurant.objects.get(id=restaurant_id)

    if request.method == 'POST':

        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        picture = request.POST.get('picture')

        vegeterian = request.POST.get('vegeterian') == 'on'

        if not picture:
            picture = 'https://www.indiafilings.com/learn/wp-content/uploads/2024/08/How-to-Start-Food-Business.jpg'

        if Item.objects.filter(
            restaurant=restaurant,
            name=name
        ).exists():
            return HttpResponse("Duplicate item!")

        Item.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            price=price,
            vegeterian=vegeterian,
            picture=picture
        )

        return redirect('open_update_menu', restaurant_id=restaurant.id)

    itemList = restaurant.items.all()

    return render(
        request,
        'delivery/update_menu.html',
        {
            'itemList': itemList,
            'restaurant': restaurant
        }
    )

def view_menu(request, restaurant_id, username):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'delivery/customer_menu.html'
                  ,{"itemList" : itemList,
                     "restaurant" : restaurant, 
                     "username":username})

def add_to_cart(request, item_id, username):
    item = Item.objects.get(id = item_id)
    customer = Customer.objects.get(username = username)

    cart, created = Cart.objects.get_or_create(customer = customer)

    cart.items.add(item)

    return render(request,'delivery/item_added.html')

def remove_from_cart(request, item_id, username):
    item = Item.objects.get(id=item_id)
    customer = Customer.objects.get(username=username)

    cart = Cart.objects.filter(customer=customer).first()

    if cart:
        cart.items.remove(item)

    return redirect('show_cart', username=username)

def show_cart(request, username):
    customer = Customer.objects.get(username = username)
    cart = Cart.objects.filter(customer=customer).first()
    items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    return render(request, 'delivery/cart.html',{"itemList" : items, "total_price" : total_price, "username":username})

def checkout(request, username):

    customer = get_object_or_404(Customer, username=username)

    cart = Cart.objects.filter(customer=customer).first()

    if not cart:
        return render(request, 'delivery/checkout.html', {
            'error': 'Your cart is empty!',
            'username': username,
        })

    cart_items = cart.items.all()

    total_price = cart.total_price()

    if not total_price or float(total_price) <= 0:
        return render(request, 'delivery/checkout.html', {
            'error': 'Your cart is empty!',
            'username': username,
        })

    # Razorpay client
    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # Convert ₹ to paise
    amount_paise = int(float(total_price) * 100)

    order_data = {
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': f'order_{customer.id}',
        'payment_capture': 1,
    }

    # Create Razorpay order
    order = client.order.create(data=order_data)

    return render(request, 'delivery/checkout.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],
        'amount_paise': amount_paise,
    })
def orders(request, username):

    customer = get_object_or_404(
        Customer,
        username=username
    )

    cart = Cart.objects.filter(
        customer=customer
    ).first()

    # Get items before clearing cart
    cart_items = cart.items.all() if cart else []

    total_price = cart.total_price() if cart else 0

    # Clear cart after order
    if cart:
        cart.items.clear()

    return render(
        request,
        'delivery/orders.html',
        {
            'username': username,
            'customer': customer,
            'cart_items': cart_items,
            'total_price': total_price,
        }
    )