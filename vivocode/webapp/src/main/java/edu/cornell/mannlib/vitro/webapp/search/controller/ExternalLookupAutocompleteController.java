/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.search.controller;

import java.io.IOException;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletResponse;

import net.sf.json.JSONArray;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.RDFNode;

import edu.cornell.mannlib.vitro.webapp.auth.permissions.SimplePermission;
import edu.cornell.mannlib.vitro.webapp.auth.requestedAction.AuthorizationRequest;
import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
import edu.cornell.mannlib.vitro.webapp.controller.ajax.VitroAjaxController;
import edu.cornell.mannlib.vitro.webapp.rdfservice.impl.RDFServiceUtils;
import edu.cornell.mannlib.vitro.webapp.search.externallookup.ExternalLookupService;
import edu.cornell.mannlib.vitro.webapp.search.externallookup.LookupResult;
import edu.cornell.mannlib.vitro.webapp.utils.dataGetter.DataGetterUtils;

/**
 * ExternalAutoCompleteController generates autocomplete content via the search
 * index.
 */

public class ExternalLookupAutocompleteController extends VitroAjaxController {

	// Called with external lookup service request
	// Given a service name along with the term for lookup
	// Will return a JSON result with information

	private static final long serialVersionUID = 1L;
	private static final Log log = LogFactory
			.getLog(ExternalLookupAutocompleteController.class);

	// private static final String TEMPLATE_DEFAULT = "autocompleteResults.ftl";

	private static final String PARAM_QUERY = "term";
	private static final String PARAM_RDFTYPE = "type";
	private static final String PARAM_MULTIPLE_RDFTYPE = "multipleTypes";
	private static final String SERVICE_URI = "serviceURI";
	private HashMap<String, String> serviceNameToClass = new HashMap<String, String>();
	private boolean hasMultipleTypes = false;

	String NORESULT_MSG = "";

	@Override
	protected AuthorizationRequest requiredActions(VitroRequest vreq) {
		return SimplePermission.USE_BASIC_AJAX_CONTROLLERS.ACTION;
	}

	@Override
	protected void doRequest(VitroRequest vreq, HttpServletResponse response)
			throws IOException, ServletException {

		try {
			String qtxt = vreq.getParameter(PARAM_QUERY);
			//type param may still be employed
			String typeParam = vreq.getParameter(PARAM_RDFTYPE);
			String serviceURI = vreq.getParameter(SERVICE_URI);



			ExternalLookupService externalLookup = getExternalLookupService(serviceURI, vreq);

			List<LookupResult> results = externalLookup.processResults(qtxt);
			//We are keeping the json object library consistent -> net.sf.json
			//NOT org.json which is a different matter
			JSONArray jsonArray = new JSONArray();
			for (LookupResult result : results) {
				// jsonArray.put(result.toMap());
				jsonArray.add(result.toJSONObject());
			}
			response.getWriter().write(jsonArray.toString());

		} catch (Throwable e) {
			log.error(e, e);
			doSearchError(response);
		}
	}



	private HashMap<String, String> getServiceInformation(String serviceURI, VitroRequest vreq) {
		//Get the information about this lookup based on the sercieURI, e.g. climateSolrLookup
		//Get the specific type, i.e. the type that is NOT external lookupservice
		//Get all the properties and then retrieve that information
		String externalLookupServiceType = "java:edu.cornell.mannlib.vitro.webapp.search.externallookup.ExternalLookupService";
		String queryStr = "SELECT ?type ?p ?o WHERE { <" + serviceURI + "> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type . \n" +
		"<" + serviceURI + "> ?p ?o . }";

		HashMap<String, String> serviceInfo = new HashMap<String, String>();
		//URI defining the lookup service itself - RDF
		serviceInfo.put("serviceURI", serviceURI);
		String serviceClass = null;
		ResultSet rs = RDFServiceUtils.sparqlSelectQuery(queryStr, vreq.getRDFService());
		while(rs.hasNext()) {
			QuerySolution qs = rs.nextSolution();
			if(qs.get("type") != null && qs.get("type").isURIResource() && qs.getResource("type").getURI() != null) {
				String typeURI = qs.getResource("type").getURI();
				//We could also filter this out in the query itself
				if(!typeURI.equals(externalLookupServiceType)) {
					serviceClass = typeURI;
					serviceInfo.put("serviceClass", serviceClass);
				}
			}
			String propertyURI = qs.getResource("p").getURI();
			//No need to recapture type - also we are only storing one value per property URI here so no need to retrieve this info if we already have it
			//This would change if we instead decided to store all possible object properties for a given property
			if(!propertyURI.equals("http://www.w3.org/1999/02/22-rdf-syntax-ns#type") &&
					!serviceInfo.containsKey(propertyURI)) {
				RDFNode varNode = qs.get("o");
				String value = null;
				if(varNode.isLiteral()) {
					value = varNode.asLiteral().getString();
				} else {
					value = varNode.asResource().getURI();
				}
				//This doesn't account for multiple values for the same property URI so this should really be a List of Strings
				serviceInfo.put(propertyURI, value);
			}
		}

		return serviceInfo;

	}

	public ExternalLookupService getExternalLookupService(String serviceURI, VitroRequest vreq)
			throws Exception {
		HashMap<String, String> serviceInfo = this.getServiceInformation(serviceURI, vreq);

		if(!serviceInfo.containsKey("serviceClass")) {
			log.error("No service class returned for service URI " + serviceURI);
			throw new Exception("No service class returned for service URI " + serviceURI);
		}
		String serviceClassURI = serviceInfo.get("serviceClass");
		//URI is of form java:.., need to get portion after java:...
		String serviceClassName = DataGetterUtils.getClassNameFromUri(serviceClassURI);
		if (serviceClassName != null) {
			ExternalLookupService externalServiceClass = null;

			Object object = null;
			try {
				Class classDefinition = Class.forName(serviceClassName);
				object = classDefinition.newInstance();
				externalServiceClass = (ExternalLookupService) object;
			} catch (InstantiationException e) {
				System.out.println(e);
			} catch (IllegalAccessException e) {
				System.out.println(e);
			} catch (ClassNotFoundException e) {
				System.out.println(e);
			}

			if (externalServiceClass == null) {
				log.error("could not find Lookup Class for " + serviceClassName);
				return null;
			}

			//Initialize this class
			externalServiceClass.initializeLookup(serviceInfo);
			return externalServiceClass;

		}

		log.debug("Service class name is null for " + serviceURI
				+ " and no lookup will occur");
		return null;

	}

	private void doNoQuery(HttpServletResponse response) throws IOException {
		// For now, we are not sending an error message back to the client
		// because
		// with the default autocomplete configuration it chokes.
		doNoSearchResults(response);
	}

	private void doSearchError(HttpServletResponse response) throws IOException {
		// For now, we are not sending an error message back to the client
		// because
		// with the default autocomplete configuration it chokes.
		doNoSearchResults(response);
	}

	private void doNoSearchResults(HttpServletResponse response)
			throws IOException {
		response.getWriter().write("[]");
	}

	// Original version of search result
	// Ours should also implement comparable to allow sorting
	/*
	 * public class SearchResult implements Comparable<Object> { private String
	 * label; private String uri; private String msType; private List<String>
	 * allMsTypes; private boolean hasMultipleTypes;
	 *
	 * SearchResult(String label, String uri, String msType, List<String>
	 * allMsTypes, boolean hasMultipleTypes, VitroRequest vreq) { if (
	 * hasMultipleTypes ) { this.label = label + " (" +
	 * getMsTypeLocalName(msType, vreq) + ")"; } else { this.label = label; }
	 * this.uri = uri; this.msType = msType; this.allMsTypes = allMsTypes; }
	 *
	 * public String getLabel() { return label; }
	 *
	 * public String getJsonLabel() { return JSONObject.quote(label); }
	 *
	 * public String getUri() { return uri; }
	 *
	 * public String getJsonUri() { return JSONObject.quote(uri); }
	 *
	 * public String getMsType() { return msType; }
	 *
	 * public List<String> getAllMsTypes() { return allMsTypes; }
	 *
	 * public String getMsTypeLocalName(String theUri, VitroRequest vreq) {
	 * VClassDao vcDao =
	 * vreq.getUnfilteredAssertionsWebappDaoFactory().getVClassDao(); VClass
	 * vClass = vcDao.getVClassByURI(theUri); String theType =
	 * ((vClass.getName() == null) ? "" : vClass.getName()); return theType; }
	 *
	 * public String getJsonMsType() { return JSONObject.quote(msType); }
	 *
	 *
	 * //Simply passing in the array in the map converts it to a string and not
	 * to an array //which is what we want so need to convert to an object
	 * instad JSONObject toJSONObject() { JSONObject jsonObj = new JSONObject();
	 * try { jsonObj.put("label", label); jsonObj.put("uri", uri); //Leaving
	 * this in for now, in case there is code out there that depends on this
	 * single string version //But this should really be changed so that the
	 * entire array is all that should be returned jsonObj.put("msType",
	 * msType); //map.put("allMsTypes", allMsTypes); JSONArray allMsTypesArray =
	 * new JSONArray(allMsTypes); jsonObj.put("allMsTypes", allMsTypesArray); }
	 * catch(Exception ex) {
	 * log.error("Error occurred in converting values to JSON object", ex); }
	 * return jsonObj; }
	 *
	 * public int compareTo(Object o) throws ClassCastException { if ( !(o
	 * instanceof SearchResult) ) { throw new ClassCastException(
	 * "Error in SearchResult.compareTo(): expected SearchResult object."); }
	 * SearchResult sr = (SearchResult) o; return
	 * label.compareToIgnoreCase(sr.getLabel()); } }
	 */
}
