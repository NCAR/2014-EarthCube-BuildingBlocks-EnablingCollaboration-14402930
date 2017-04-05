/* $This file is distributed under the terms of the license in /doc/license.txt$ */
/*
 * This is the implementation of looking up information from PostGres
 */

package edu.cornell.mannlib.vitro.webapp.search.externallookup.impl;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.StringWriter;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;

import javax.servlet.http.HttpServletRequest;

import net.sf.json.JSONArray;
import net.sf.json.JSONObject;
import net.sf.json.JSONSerializer;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import edu.cornell.mannlib.vitro.webapp.modules.searchEngine.SearchQuery;
import edu.cornell.mannlib.vitro.webapp.search.VitroSearchTermNames;
import edu.cornell.mannlib.vitro.webapp.search.externallookup.ExternalLookupService;
import edu.cornell.mannlib.vitro.webapp.search.externallookup.LookupResult;

public class SolrLookup implements ExternalLookupService {
	private static final Log log = LogFactory.getLog(SolrLookup.class);

	//private String solrAPI = "http://climate-dev.library.cornell.edu:8080/vivosolr/collection1/select?";
	private String solrAPI = null;
	private String serviceURI = null;
	private String serviceLabel = null;
	//The Solr instance corresponds to an actual
	private String endpointURL = null;
	private String endpointLabel = null;
	private String endpointURLKey = "http://vivo.earthcollab.edu/individual/hasEndpointURL"; //really ACCESS URL - i.e. where to actually get the information on the individual, the VIVO URL
	private String endpointLabelKey = "http://vivo.earthcollab.edu/individual/hasEndpointLabel";
	private String solrAPIKey = "http://vivo.earthcollab.edu/individual/hasSolrAPIURL";
	private String serviceURIKey = "serviceURI";
	private String serviceLabelKey = "http://www.w3.org/2000/01/rdf-schema#label";
	private String jsonFormatParameter = "wt=json";

	//initialize with URL
	//There may be a better way to do this - will need to review
	public void initializeLookup(HashMap<String, String> inputParameters) throws Exception {
		//Check for solrAPI
		if(inputParameters.containsKey(solrAPIKey)) {
			this.solrAPI = inputParameters.get(solrAPIKey);
		} else {
			log.error("Solr lookup cannot be initialized as no Solr API has been passed");
			throw new Exception("Solr lookup cannot be initialized as no Solr API has been passed");
		}

		if(inputParameters.containsKey(endpointURLKey)) {
			this.endpointURL = inputParameters.get(endpointURLKey);
			log.debug("Endpoint URL is " + this.endpointURL);

		}

		if(inputParameters.containsKey(endpointLabelKey)) {
			this.endpointLabel = inputParameters.get(endpointLabelKey);
			log.debug("Endpoint Label is " + this.endpointLabel);
		}

		if(inputParameters.containsKey(serviceURIKey)) {
			this.serviceURI = inputParameters.get(serviceURIKey);
			log.debug("Service URI is " + this.serviceURI);
		}

		if(inputParameters.containsKey(serviceLabelKey)) {
			this.serviceLabel = inputParameters.get(serviceLabelKey);
			log.debug("Service Label is " + this.serviceLabel);
		}
	}


	// Returns actual results
	public List<LookupResult> processResults(String term) throws Exception {
		List<LookupResult> results = new ArrayList<LookupResult>();
		try {
			results = this.lookupSolrEntities(term);
		} catch(Exception ex) {
			log.error("Throw error when trying to lookup results", ex);
			//ex.printStackTrace();
		}
		return results;
	}

	// Hopefully can replace this with API call
	// Or somehow replace this with the json being read in at the beginning

	private List<LookupResult> lookupSolrEntities(String term) {
		String results = getSolrResults(term);
		if(!StringUtils.isEmpty(results)) {
			//Process lookup results and return
			//TODO: Handle Solr error messages that might come back in this string
			return processSolrResults(results);
		}
		return null;
	}

	//
	private String getSolrResults(String term) {
		String results = null;
		String queryTerm = this.getNameQuery(term);
		String solrURL = solrAPI + "q="+ queryTerm + "&" + jsonFormatParameter;
		try {

			StringWriter sw = new StringWriter();
			URL rss = new URL(solrURL);

			BufferedReader in = new BufferedReader(new InputStreamReader(
					rss.openStream()));
			String inputLine;
			while ((inputLine = in.readLine()) != null) {
				sw.write(inputLine);
			}
			in.close();

			results = sw.toString();
			log.debug("Results string is " + results);
			// System.out.println("results before processing: "+results);

		} catch (Exception ex) {
			log.error("Exception occurred in retrieving results",ex);
			//ex.printStackTrace();
			return null;
		}
		return results;

	}

	//Process the results from Solr
	private List<LookupResult> processSolrResults(String results) {
		List<LookupResult> solrResults = new ArrayList<LookupResult>();
		if (StringUtils.isNotEmpty(results)) {
			try {
				JSONObject resultsJSON = (JSONObject) JSONSerializer.toJSON(results);
				if(resultsJSON.containsKey("response")) {

					JSONObject response = resultsJSON.getJSONObject("response");
					if(response.containsKey("docs")) {
						JSONArray docs = response.getJSONArray("docs");
						//Now create the lookup result
						for(Object doc:docs) {
							LookupResult lr = this.generateLookupResultFromDocument((JSONObject) doc);
							if(lr != null) {
								solrResults.add(lr);
							}
						}
					}
				}

			} catch (Exception ex) {
				log.error("Error message in converting JSON to list", ex);
				//ex.printStackTrace();

				throw ex;
			}
		}

		//This is just a test for string utils, will take this out

		return solrResults;
	}

	private LookupResult generateLookupResultFromDocument(JSONObject doc) {
		LookupResult lr = null;
		//    public LookupResult(String label, String typeString, String typeURI, String idString,String idURI, String serviceName, String serviceURI) {
		 String uri = doc.getString(VitroSearchTermNames.URI);
		 //This can be actually multiple names, we just want the first one
		 JSONArray namesArray = doc.getJSONArray(VitroSearchTermNames.NAME_RAW);
		 String name = namesArray.getString(0);
        // String name = doc.getString(VitroSearchTermNames.NAME_RAW);
         //There may be multiple most specific types, sending them all back

         //Assuming these will get me string values
         JSONArray mstObjValues = doc.getJSONArray(VitroSearchTermNames.MOST_SPECIFIC_TYPE_URIS);
         List<String> mstObjURIs = new ArrayList<String>();
         for(Object j:mstObjValues) {

        	mstObjURIs.add((String) j);
        	//Is there a way to get the label FROM VIVO if not wihtin Solr?
         }
         //Pick one and then utilize to pass back but for now, put in the additional info object
         //mstObjValues.toArray(String[])
         //List<String> mstValues = Arrays.asList(mstStringValues);
        // for(JSONObject)
         Collections.sort(mstObjURIs);
         String typeURI = "";
         if(mstObjURIs.size() > 0) {
        	 typeURI = mstObjURIs.get(0);
         }
         lr = new LookupResult(name, null, typeURI, null,uri, this.serviceLabel, this.serviceURI);
         JSONObject additionalInfo = new JSONObject();
         additionalInfo.put("mostSpecificTypes",mstObjValues);
         lr.setAdditionalInfo(additionalInfo);
         //Endpoint info, hardcoded here but would expect to retrieve this from a central lookup
         JSONObject endpointInfo = new JSONObject();
         endpointInfo.put("URL",this.endpointURL);
         endpointInfo.put("label",this.endpointLabel);
         lr.setEndpointInfo(endpointInfo);

		return lr;
	}


	//Copying from autocomplete controller so will need to refactor this later
	//Assumption (MAJOR): That this is a VIVO or Vitro Solr lookup
	//Another Solr lookup implementation would have a different mechanism for looking up items
	 private String getNameQuery(String queryStr) {
		 //Not trimming as ending with space designates something in the main code
		 //TODO: Look at what this means
	        //queryStr = queryStr.trim();
	        queryStr = this.getTokenizedNameQuery(queryStr);
	        return queryStr;
	    }

	 //Adapted from autocomplete controller, this is what is actually being used
	 private String getTokenizedNameQuery(String queryStr) {
	        String acTermName = VitroSearchTermNames.AC_NAME_STEMMED;
	        String nonAcTermName = VitroSearchTermNames.NAME_STEMMED;
	        String acQueryStr;

	        if (queryStr.endsWith(" ")) {
	            acQueryStr = makeTermQuery(nonAcTermName, queryStr, true);
	        } else {
	            int indexOfLastWord = queryStr.lastIndexOf(" ") + 1;
	            List<String> terms = new ArrayList<String>(2);

	            String allButLastWord = queryStr.substring(0, indexOfLastWord);
	            if (StringUtils.isNotBlank(allButLastWord)) {
	                terms.add(makeTermQuery(nonAcTermName, allButLastWord, true));
	            }

	            String lastWord = queryStr.substring(indexOfLastWord);
	            if (StringUtils.isNotBlank(lastWord)) {
	                terms.add(makeTermQuery(acTermName, lastWord, false));
	            }

	            acQueryStr = StringUtils.join(terms, " AND ");
	        }

	        log.debug("Tokenized name query string = " + acQueryStr);
	        return acQueryStr;

	    }

	    private String makeTermQuery(String term, String queryStr, boolean mayContainWhitespace) {
	        if (mayContainWhitespace) {
	            queryStr = "\"" + escapeWhitespaceInQueryString(queryStr) + "\"";
	        }
	        return term + ":" + queryStr;
	    }


	    private String escapeWhitespaceInQueryString(String queryStr) {
	        // The search engine wants whitespace to be escaped with a backslash
	        return queryStr.replaceAll("\\s+", "\\\\ ");
	    }
}
