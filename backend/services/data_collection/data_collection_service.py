# Enhance the data collection service with additional sources
# backend/services/data_collection/data_collection_service.py

class DataCollectionService:
    def __init__(self):
        self.sources = {
            'zillow': ZillowScraper(),
            'realtor': RealtorApiConnector(),  # New connector needed
            'mls': MLSConnector()  # New connector needed
        }
    
    async def collect_from_all_sources(self, search_params):
        """Collect property data from all sources concurrently"""
        tasks = []
        for source_name, source in self.sources.items():
            tasks.append(self.collect_from_source(source, search_params))
        
        all_properties = []
        results = await asyncio.gather(*tasks)
        for result in results:
            all_properties.extend(result)
        
        return all_properties