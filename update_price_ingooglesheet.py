import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import  os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR,"Json_cr","metalprices-18be5626fa37.json")
PRICE_LIST_SHEET_NAME = ("cable")

def get_current_time():
    # get the current date time
    now = datetime.now()
    # create the forma
    current_time = now.strftime("%H:%M:%S  %d/%m/%Y")
    return current_time

def up_date_price(co_price,al_price,shekel_eru):
    # setting aces
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # get ket from computer
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)

    # connect to google sheet
    client = gspread.authorize(creds)

    # open sheet
    sheet = client.open(PRICE_LIST_SHEET_NAME).sheet1

    #get the current time
    last_update = get_current_time()


    # up date the copper price
    sheet.update_cell(2,2,co_price)
    # Update the last update time
    sheet.update_cell(2, 3, last_update)

    # update the aluminum  price
    sheet.update_cell(3,2,al_price)
    # Update the last update time
    sheet.update_cell(3, 3, last_update)

    # Update the eru price
    sheet.update_cell(4, 2, shekel_eru)
    sheet.update_cell(4, 3, last_update)

    #read the updated sheet
    data = sheet.get_all_records()

    #compare the result
    if data[0].get('price eru') == co_price\
            and data[1].get('price eru') == al_price\
            and data[2].get('price eru') == shekel_eru:
        return True
    else:
        return False



def main():
    up_date_price(9001,9002,3.9)


if __name__ == "__main__":

    main()