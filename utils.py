import random
import datetime
import os
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
    now_month = int(datetime.datetime.now().strftime("%m"))
    new_min = now
    new_max = now + 10
    month_min = 1
    month_max = 12
    year = random.randint(new_min, new_max)
    if year == new_min:
        if now_month == 12:
            date = f"{str(random.randint(month_min, month_max)).rjust(2, '0')}/{year + 1}"
        else:
            date = f"{str(random.randint(now_month + 1, month_max)).rjust(2, '0')}/{year}"
    else:
        date = f"{str(random.randint(month_min, month_max)).rjust(2, '0')}/{year}"

    return {"cvv": cvv, "date": date}


def clean_dir(dir):
    try:
        for i in os.listdir(dir):
            os.remove(f"{dir}/{i}")
    except:
        os.mkdir(dir)