from amadeus import Client, ResponseError, Location
from dotenv import load_dotenv
import os
load_dotenv()

amadeus = Client(
    client_id= os.getenv('AMAD_ID'),
    client_secret= os.getenv('AMAD_SECRET')
)

try:
    # Example: find locations matching “LON”
    response = amadeus.reference_data.locations.get(
        keyword='LON',
        subType=Location.AIRPORT
    )
    print(response.data)
except ResponseError as error:
    print(error)