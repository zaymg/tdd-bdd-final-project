######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #

    def test_get_product(self):
        """It should Get a single Product"""
        # get the id of a product
        test_product = self._create_products(1)[0]
        # make a self.client.get request to the API endpoint and store the result in the variable named response
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        # assert that the resp.status_code is status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # get the data from resp.get_json()
        data = response.get_json()
        # assert that data["name"] equals the test_product.name
        self.assertEqual(data["name"], test_product.name)
    
    def test_get_product_not_found(self):
        """It should not Get a Product thats not found"""
        # send a self.client.get() request to the BASE_URL with an invalid product ID (e.g., 0)
        response = self.client.get(f"{BASE_URL}/0")
        # assert that the resp.status_code is status.HTTP_404_NOT_FOUND
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])
    
    def test_update_product(self):
        """It should Update an existing Product"""
        # create a product to update
        test_product = ProductFactory()
        # send a self.client.post() request to the BASE_URL with a json payload of test_product.serialize()
        response = self.client.post(BASE_URL, json=test_product.serialize())

        # assert that the resp.status_code is status.HTTP_201_CREATED
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # UPDATE THE PRODUCT
        # get the data from resp.get_json() as new_product
        new_product = response.get_json()

        # change new_account["description"] to unknown
        new_product["description"] = "unknown"

        # send a self.client.put() request to the BASE_URL with a json payload of new_product
        response = self.client.put(f"{BASE_URL}/{new_product['id']}", json=new_product)

        # assert that the resp.status_code is status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # get the data from resp.get_json() as updated_product
        updated_product = response.get_json()

        # assert that the updated_product["description"] is whatever you changed it to
        self.assertEqual(updated_product["description"], "unknown")
    
    def test_delete_product(self):
        """It should Delete a Product"""

        # create a list products containing 5 products using the _create_products() method. 
        products = self._create_products(5)

        # call the self.get_product_count() method to retrieve the initial count of products before any deletion
        product_count = 5

        # assign the first product from the products list to the variable test_product
        test_product = products[0]

        # send a self.client.delete() request to the BASE_URL with test_product.id
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")

        # assert that the resp.status_code is status.HTTP_204_NO_CONTENT
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check if the response data is empty 
        self.assertEqual(len(response.data), 0)

        # send a self.client.get request to the same endpoint that was deleted to retrieve the deteled product
        response = self.client.get(f"{BASE_URL}/{test_product.id}")

        # assert that the resp.status_code is status.HTTP_404_NOT_FOUND to confirm deletion of the product
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # retrieve the count of products after the deletion operation
        new_count = self.get_product_count()

        # check if the new count of products is one less than the initial count
        self.assertEqual(new_count, product_count - 1)
    
    def test_get_product_list(self):
        """It should Get a list of Products"""
        self._create_products(5)
        # send a self.client.get() request to the BASE_URL
        response = self.client.get(BASE_URL)

        # assert that the resp.status_code is status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # get the data from resp.get_json()
        data = response.get_json()

        # assert that the len() of the data is 5 (the number of products you created)
        self.assertEqual(len(data), 5)

    def test_query_by_name(self):
        """It should Query Products by name"""
        products = self._create_products(5)
        # extract the name of the first product in the products list and assigns it to the variable test_name
        test_name = products[0].name

        # count the number of products in the products list that have the same name as the test_name
        name_count = len([product for product in products if product.name == test_name])

        # send an HTTP GET request to the URL specified by the BASE_URL variable, along with a query parameter "name"
        response = self.client.get(
            BASE_URL, query_string=f"name={quote_plus(test_name)}"
        )

        # assert that response status code is 200, indicating a successful request (HTTP 200 OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # retrieve the JSON data from the response
        data = response.get_json()

        # assert that the length of the data list (i.e., the number of products returned in the response) is equal to name_count
        self.assertEqual(len(data), name_count)
        
        # use a for loop to iterate through the products in the data list and checks if each product's name matches the test_name
        for product in data:
            self.assertEqual(product["name"], test_name)
        
    def test_query_by_category(self):
        """It should Query Products by category"""
        products = self._create_products(10)
        # retrieves the category of the first product in the products list and assigns it to the variable category
        category = products[0].category
       
        # create a list named found, containing products from the products list whose category matches the category variable
        found = [product for product in products if product.category == category]
        
        # check the count of products match the specified category and assign it to the variable found_count
        found_count = len(found)
        
        # Log a debug message indicating the count and details of the products found
        logging.debug("Found Products [%d] %s", found_count, found)

        # send an HTTP GET request to the URL specified by the BASE_URL variable, along with a query parameter "category"
        response = self.client.get(BASE_URL, query_string=f"category={category.name}")

        # assert that response status code is 200, indicating a successful request (HTTP 200 OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # retrieve the JSON data from the response
        data = response.get_json() 

        # assert that the length of the data list (i.e., the number of products returned in the response) is equal to found_count
        self.assertEqual(len(data), found_count)

        # use a for loop to check each product in the data list and verify that all returned products belong to the queried category
        for product in data:
            self.assertEqual(product["category"], category.name)

    def test_query_by_availability(self):
        """It should Query Products by availability"""
        products = self._create_products(10)
        # list named available_products is initialized to store the products based on their availability status
        available_products = [product for product in products if product.available is True]      
        
        # store the  count of available products.
        available_count = len(available_products) 

        # Log a debug message indicating the count and details of the available products
        logging.debug("Found Products [%d] %s", available_count, available_products)

        # send an HTTP GET request to the URL specified by the BASE_URL variable, along with a query parameter "available" set to true.
        response = self.client.get(
            BASE_URL, query_string="available=true"
        )
        # assert that response status code is 200, indicating a successful request (HTTP 200 OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # retrieve the JSON data from the response
        data = response.get_json()

        # assert that the length of the data list (i.e., the number of products returned in the response) is equal to available_count
        self.assertEqual(len(data), available_count)

        # use a for loop to check each product in the data list and verify that the "available" attribute of each product is set to True
        for product in data:
            self.assertEqual(product["available"], True)

        

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
