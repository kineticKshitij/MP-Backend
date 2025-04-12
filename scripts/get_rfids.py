from pymongo import MongoClient

def get_all_rfids():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['minor_project_db']
    
    # Query all employees with RFID cards
    rfid_data = db.Home_employeesignup.find(
        {"rfid": {"$exists": True, "$ne": None}},
        {"rfid": 1, "name": 1, "_id": 0}
    )
    
    print("\nRFID Cards Assigned:")
    print("-" * 40)
    for record in rfid_data:
        print(f"Name: {record['name']:<20} RFID: {record['rfid']}")
    
    client.close()

if __name__ == "__main__":
    get_all_rfids()