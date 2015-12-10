/* $This file is distributed under the terms of the license in /doc/license.txt$ */
/*
* This is the interface for getting results back from external lookup services.
*/



package edu.cornell.mannlib.vitro.webapp.search.externallookup;

import java.util.HashMap;
import java.util.List;



public interface ExternalLookupService {

	/**
	 * @param term
	 * @return list of results that match or start with the given term
	 */
	List<LookupResult> processResults(String term) throws Exception;
	
	/**
	 * @param HashMap<String, String> inputParameters
	 * Pass hashmap of parameters which can be used to instantiate the external service lookup implementation if need be
	 */
	
	void initializeLookup(HashMap<String, String> inputParameters) throws Exception;

	
}
