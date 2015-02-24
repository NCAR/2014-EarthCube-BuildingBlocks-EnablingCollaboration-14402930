#-*- coding: utf-8 -*- 
import sys
import unittest
import scrapeawds as scraper

'''
    @author kmaull@ucar.edu
'''
class ScraperTest(unittest.TestCase):
    def setUp(self):
        """ Setting up for the test """
        print "ScraperTest:setUp_"
             
    def tearDown(self):
        """Cleaning up after the test"""
        print "ScraperTest:tearDown_"
     
    def test_RetrievePage(self):
        id = "0120736"
        
        # retrieve a page
        page = scraper.retrieve_awd_page(grant_id=id) 
        
        self.assertNotEqual(page,None,"Page retrieval returned unexpected result None")
        
        print "ScraperTest:test_RetrievePage"


    def test_ParsePageData_Positive(self):
        id = "0120736"

        # retrieve a page
        page = scraper.retrieve_awd_page(grant_id=id) 
                
        # parse this page 
        data = scraper.parse_award_page_htm (grant_id=id, htm_input_str=page)

        self.assertNotEqual(data['publications'],[],"Page data object retrieval returned unexpected result None")
        
        print "ScraperTest:test_ParsePageData_Positive"

    def test_ParsePageData_Negative(self):
        id = "012073-6"

        # retrieve a page
        page = scraper.retrieve_awd_page(grant_id=id) 
                
        # parse this page 
        data = scraper.parse_award_page_htm (grant_id=id, htm_input_str=page)

        self.assertEqual(data['publications'],[],"Page data object retrieval returned unexpected result")
        self.assertEqual(data['books'],[],"Page data object retrieval returned unexpected result")

        print "ScraperTest:test_ParsePageData_Negative"


    def test_BatchRetrieve(self):
        grant_ids = ['0732362','0732382','0732428','0732430','0732640']
                
        processed = scraper.batch_retrieve(grant_ids,store_json=True)
        
        self.assertEqual(len(processed),len(grant_ids),"Number of results returned not equal")
        for i in range(0,len(grant_ids)):
            self.assertEqual(processed[i]['id'],grant_ids[i],"Grant ids returned unexpected result")
            
        print "ScraperTest:test_BatchRetrieve"
        
# Run the test case
if __name__ == '__main__':
    basicSuite = unittest.TestLoader().loadTestsFromTestCase(ScraperTest)