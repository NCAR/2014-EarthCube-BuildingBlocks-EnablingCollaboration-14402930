/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.edit.n3editing.configuration.preprocessors;

import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.Literal;
import org.apache.jena.rdf.model.Resource;

import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.BaseEditSubmissionPreprocessorVTwo;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationUtils;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationVTwo;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.MultiValueEditSubmission;
import edu.cornell.mannlib.vitro.webapp.modelaccess.ModelAccess;
import edu.cornell.mannlib.vitro.webapp.rdfservice.RDFService;
import edu.cornell.mannlib.vitro.webapp.rdfservice.impl.RDFServiceUtils;

//Check whether the access or endpoint URL and label already exists within the system

public class ExternalEntityLookupSubmissionPreprocessor extends
		BaseEditSubmissionPreprocessorVTwo {

	protected static final Log log = LogFactory
			.getLog(ExternalEntityLookupSubmissionPreprocessor.class.getName());
	protected RDFService rdfService = null;

	private static MultiValueEditSubmission submission = null;
	private static String endpointURL = null;
	private static String endpointLabel = null;

	// String datatype

	// Will be editing the edit configuration as well as edit submission here

	public ExternalEntityLookupSubmissionPreprocessor(EditConfigurationVTwo editConfig) {
		super(editConfig);

	}

	public void preprocess(MultiValueEditSubmission inputSubmission,
			VitroRequest vreq) {
		submission = inputSubmission;
		this.rdfService = ModelAccess.on(vreq).getRDFService();
		// Keep the original submission values separately

		copySubmissionValues();
		String existingURI = getExistingURIForAccessEndpoint();
		if (!StringUtils.isEmpty(existingURI)) {
			log.debug("URI exists: " + existingURI);
			replaceEndpointURI(existingURI);
		}

	}

	private String getExistingURIForAccessEndpoint() {
		String URI = null;
		//check to see if
		if (endpointURL != null ) {
			// Query the system to see if any uris exist with this particular
			// identifier and type
			log.debug("Checking existing URIs for endpoint URL " + endpointURL);
			URI = this.getSparqlQueryResult();

		}
		return URI;
	}

	//Within submission, replace the URI with the existing URI
	private void replaceEndpointURI(String existingURI) {
		String[] URIValues = new String[1];
		URIValues[0] = existingURI;
		submission.addUriToForm(editConfiguration, "endpointURI", URIValues);
		log.debug("Adding URI to form " + existingURI);

	}



	private String getSparqlQueryResult() {
		String endpointURI = null;
		String query = "SELECT ?endpointURI WHERE {?endpointURI <http://vivoweb.org/ontology/core#externalURL> '"
				+ endpointURL
				+ "' . }";
		log.debug("Query to be executed to check if this endpoint URI already exists is "
				+ query);

		try {

			ResultSet results = RDFServiceUtils.sparqlSelectQuery(query,
					rdfService);
			while (results.hasNext()) {
				QuerySolution qs = results.nextSolution();
				if (qs.get("endpointURI") != null
						&& qs.get("endpointURI").isResource()) {

					Resource endpointResource = qs.getResource("endpointURI");
					endpointURI = endpointResource.getURI();
				}
			}

		} catch (Throwable t) {
				log.error("Error in executing sparql query to retrieve any existing geographies with the same geometry type and uid");
				log.error(t, t);
		}

		if (log.isDebugEnabled()) {
			log.debug("query: '" + query + "'");

		}

		return endpointURI;
	}

	// Since we will change the uris and literals from form, we should make
	// copies
	// of the original values and store them, this will also make iterations
	// and updates to the submission independent from accessing the values
	private void copySubmissionValues() {
		// Retrieve the geometry type and uid of the element added
		Map<String, List<Literal>> literalsFromForm = submission
				.getLiteralsFromForm();
		Map<String, List<String>> transformed = EditConfigurationUtils
				.transformLiteralMap(literalsFromForm);
		String endpointURLKey = "endpointURL";
		String endpointLabelKey = "endpoinstLabel";
		endpointURL = getTransformedValue(transformed, endpointURLKey);
		endpointLabel = getTransformedValue(transformed, endpointLabelKey);

	}

	private String getTransformedValue(Map<String, List<String>> transformed,
			String key) {
		String value = null;
		if (transformed.containsKey(key)) {
			List<String> values = transformed.get(key);
			if (values.size() > 0) {
				value = transformed.get(key).get(0);
			}
		}
		return value;
	}



}
