import random
import datetime

 # IIN For Banking Industry(6 digits)
def luhn(num):
    card_no = [int(i) for i in str(num)]  # To find the checksum digit on
    card_num = [int(i) for i in str(num)]  # Actual account number
    seventh_15 = random.sample(range(9), 9)  # Acc no (9 digits)
    for i in seventh_15:
        card_no.append(i)
        card_num.append(i)
    for t in range(0, 15, 2):  # odd position digits
        card_no[t] = card_no[t] * 2
    for i in range(len(card_no)):
        if card_no[i] > 9:  # deduct 9 from numbers greater than 9
            card_no[i] -= 9
    s = sum(card_no)
    mod = s % 10
    check_sum = 0 if mod == 0 else (10 - mod)
    card_num.append(check_sum)
    card_num = [str(i) for i in card_num]
    return ''.join(card_num)


def cvv_date():
    minimum = 0
    maximum = 9
    cvv = f"{random.randint(minimum, maximum)}{random.randint(minimum, maximum)}{random.randint(minimum, maximum)}"
    now = int(datetime.datetime.now().strftime("%y"))
    new_min = now
    new_max = now + 10
    month_min = 1
    month_max = 12
    date = f"{str(random.randint(month_min, month_max)).rjust(2, '0')}/{random.randint(new_min, new_max)}"
    return {"cvv": cvv, "date": date}