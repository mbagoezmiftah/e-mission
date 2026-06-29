import globals
# Module to set global variable to save the data - this lets us share data across callbacks.
# NOTE: This may not suitable for a hosted/multi-user situation!!
# Set the global data
def setDataStore(data):
    globals.dataStore = data
