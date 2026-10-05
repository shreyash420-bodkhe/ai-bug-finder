import random

print("Guess The Number Game")
print("Guess a number between 1 and 100")

number = random.randint(1, 100)
attempts = 0

while True:
    try:
        guess = int(input("Enter your guess: "))
        attempts += 1

        if guess < 1 or guess > 100:
            print("Enter a number between 1 and 100")
            continue

        if guess < number:
            print("Too low!")
        elif guess > number:
            print("Too high!")
        else:
            print("Correct!")
            print("You guessed it in", attempts, "attempts")
            break
    except ValueError:
        print("Please enter a valid number")

print("Game Over!")