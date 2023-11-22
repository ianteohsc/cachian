from cachian import Cachian

class PatientDB:

    @Cachian() #LRU caching defaulting to 10,000 items
    def get_by_id(self, id):
        pass

    @Cachian(maxsize=100) #LRU caching with 100 items
    def get_by_id2(self, id):
        pass        

    @Cachian(ttl=60) #TTL caching with TTL at 60 secs
    def get_latest_10_patient(self):
        pass
    
    #Split cache clearing by first args ie. id
    @Cachian(partition_attr=1)
    def get_by_id3(self, id):
        pass

    #TTL, LRU & partition caching, whichever miss first
    @Cachian(maxsize=100,ttl=60,partition_attr=1)
    def get_by_id4(self,id):
        pass


#Can be used with standalone functions
@Cachian()
def count_patient_name_len(patient_name):
    return len(patient_name)