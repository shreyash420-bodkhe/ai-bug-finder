# 120-Line Python Program Intentionally Filled With Every Type of Error
# Designed for debugging practice, code review, or testing linters.

import os
import math
import random
# ERROR: Importing a module that does not exist (ModuleNotFoundError)
import non_existent_module_xyz 

# Global variable for testing
GLOBAL_COUNT = "100"

def calculate_area(radius):
    # ERROR: Using an undefined variable (NameError)
    # ERROR: Indentation error on the next line (mixed spaces/tabs)
	area = math.pi * (radus ** 2)
    return area

def process_user_data(user_list):
    # ERROR: Logical error - modifying a list while iterating over it
    for user in user_list:
        if user == "Admin":
            user_list.remove(user)
            
    # ERROR: Syntax Error - missing colon at the end of the if statement
    if len(user_list) > 0
        print("Users remain")
    
    # ERROR: Index Error - trying to access an element out of bounds
    print("The last user is: " + user_list[105])
    return user_list

def mathematical_chaos(a, b):
    # ERROR: ZeroDivisionError if b is 0, but forced here by a logical mistake
    result = a / (b - b) 
    
    # ERROR: Type Error - trying to add a string to an integer
    total = result + "20"
    
    # ERROR: Local variable referenced before assignment (UnboundLocalError)
    print(temporary_value)
    temporary_value = 50
    
    return total

class Vehicle:
    # ERROR: Syntax Error - misspelled '__init__' method
    def __int__(self, make, model):
        self.make = make
        self.model = model
    
    def display_info(self):
        # ERROR: Attribute Error - self.year was never defined
        print(f"Vehicle: {self.make} {self.model} ({self.year})")

def file_operations():
    # ERROR: FileNotFoundError - opening a non-existent file without try-except
    file = open("completely_imaginary_file.txt", "r")
    content = file.read()
    
    # ERROR: Resource Leak - file is never closed if an error happens above
    file.close()
    return content

def list_and_dict_errors():
    my_list = [1, 2, 3, 4, 5]
    my_dict = {"name": "Alice", "age": 25}
    
    # ERROR: Key Error - key 'salary' does not exist
    print(my_dict["salary"])
    
    # ERROR: Type Error - lists cannot be used as dictionary keys
    bad_dict = {my_list: "corrupted"}
    
    # ERROR: Value Error - unpacking too many values
    x, y = my_list 
    
    return x, y

def string_manipulation():
    greeting = "Hello World"
    
    # ERROR: Type Error - strings are immutable, cannot assign to items
    greeting[0] = "h"
    
    # ERROR: Attribute Error - string has no 'reverse' attribute
    reversed_greeting = greeting.reverse()
    
    return reversed_greeting

def recursion_nightmare(number):
    # ERROR: Infinite Recursion (RecursionError) - missing a base case
    print(f"Current recursion number: {number}")
    return recursion_nightmare(number + 1)

def scope_confusion():
    # ERROR: Trying to increment a global string variable as an integer
    GLOBAL_COUNT = GLOBAL_COUNT + 1
    return GLOBAL_COUNT

def syntax_galore_and_logic_flops():
    # ERROR: Syntax Error - using a reserved keyword as a variable name
    pass = "not allowed"
    
    # ERROR: Logical Error - string comparison with wrong capitalization
    if "admin" == "Admin":
        print("Access granted")
        
    # ERROR: Syntax Error - single quotes not closed properly
    print('Unclosed string literal...)
    
    # ERROR: Memory Error simulation (will crash if executed)
    huge_list = [i for i in range(1000000000000000)]
    return huge_list

def final_mess():
    # ERROR: OverflowError - floating point limits exceeded
    huge_float = math.exp(1000)
    
    # ERROR: Evaluation Error using dangerous/broken eval
    eval("if x = 5:") 
    
    return huge_float

# --- MAIN EXECUTION BLOCK ---
# This block attempts to run everything, triggering immediate crashes.
if __name__ == "__main__":
    print("Starting the ultimate broken Python program...")
    
    # Triggering errors one by one
    print(calculate_area(5))
    
    sample_users = ["Alice", "Bob", "Admin"]
    process_user_data(sample_users)
    
    mathematical_chaos(10, 5)
    
    my_car = Vehicle("Toyota", "Corolla")
    my_car.display_info()
    
    file_operations()
    list_and_dict_errors()
    string_manipulation()
    recursion_nightmare(1)
    scope_confusion()
    syntax_galore_and_logic_flops()
    final_mess()
    
    print("If you see this line, a miracle occurred and no errors were caught.")
