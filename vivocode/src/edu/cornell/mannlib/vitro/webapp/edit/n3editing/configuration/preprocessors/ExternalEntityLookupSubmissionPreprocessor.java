///* $This file is distributed under the terms of the license in /doc/license.txt$ */
//
//package edu.cornell.mannlib.vitro.webapp.edit.n3editing.configuration.preprocessors;
//
//import java.util.ArrayList;
//import java.util.HashMap;
//import java.util.HashSet;
//import java.util.List;
//import java.util.Map;
//
//import net.sf.json.JSON;
//import net.sf.json.JSONArray;
//import net.sf.json.JSONSerializer;
//
//import org.apache.commons.lang.StringUtils;
//import org.apache.commons.logging.Log;
//import org.apache.commons.logging.LogFactory;
//
//import com.hp.hpl.jena.ontology.OntModel;
//import com.hp.hpl.jena.query.Query;
//import com.hp.hpl.jena.query.QueryExecution;
//import com.hp.hpl.jena.query.QueryExecutionFactory;
//import com.hp.hpl.jena.query.QueryFactory;
//import com.hp.hpl.jena.query.QuerySolution;
//import com.hp.hpl.jena.query.ResultSet;
//import com.hp.hpl.jena.rdf.model.Literal;
//import com.hp.hpl.jena.rdf.model.Resource;
//import com.hp.hpl.jena.vocabulary.OWL;
//import com.hp.hpl.jena.vocabulary.RDF;
//import com.hp.hpl.jena.vocabulary.RDFS;
//import com.hp.hpl.jena.vocabulary.XSD;
//
//import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
//import edu.cornell.mannlib.vitro.webapp.dao.WebappDaoFactory;
//import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.BaseEditSubmissionPreprocessorVTwo;
//import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationUtils;
//import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationVTwo;
//import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.MultiValueEditSubmission;
//import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.fields.FieldVTwo;
//import edu.cornell.mannlib.vitro.webapp.modelaccess.ModelAccess;
//import edu.cornell.mannlib.vitro.webapp.rdfservice.RDFService;
//import edu.cornell.mannlib.vitro.webapp.rdfservice.impl.RDFServiceUtils;
//
////Check whether the access or endpoint URL and label already exists within the system
//
//public class ExternalEntityLookupSubmissionPreprocessor extends
//		BaseEditSubmissionPreprocessorVTwo {
//
//	protected static final Log log = LogFactory
//			.getLog(ExternalEntityLookupSubmissionPreprocessor.class.getName());
//	protected RDFService rdfService = null;
//
//	private static MultiValueEditSubmission submission = null;
//	private static String endpointURI = null;
//	private static String endpointLabel = null;
//
//	// String datatype
//
//	// Will be editing the edit configuration as well as edit submission here
//
//	public ExternalEntityLookupSubmissionPreprocessor(EditConfigurationVTwo editConfig) {
//		super(editConfig);
//
//	}
//
//	public void preprocess(MultiValueEditSubmission inputSubmission,
//			VitroRequest vreq) {
//		submission = inputSubmission;
//		this.rdfService = ModelAccess.on(vreq).getRDFService();
//		// Keep the original submission values separately
//
//		copySubmissionValues();
//		String existingURI = getExistingURIForAccessEndpoint();
//		if (!StringUtils.isEmpty(existingURI)) {
//			log.debug("URI exists: " + existingURI);
//			replaceEndpointURI(existingURI);
//		}
//
//	}
//
//	private String getExistingURIForAccessEndpoint() {
//		String URI = null;
//		// the identifier and type string together form the unique
//		// identification for a geometry type, as identifier
//		// is only unique for a given type
//		if (objectIdentifier != null && objectTypeString != null) {
//			// Query the system to see if any uris exist with this particular
//			// identifier and type
//			log.debug("Checking existing geographies for " + objectIdentifier + " - " + objectTypeString);
//			URI = this.getSparqlQueryResult();
//			
//		}
//		return URI;
//	}
//
//	//Within submission, replace the URI with the existing URI
//	private void replaceEndpointURI(String existingURI) {
//		String[] URIValues = new String[1];
//		URIValues[0] = existingURI;
//		submission.addUriToForm(editConfiguration, "endpointURI", URIValues);
//		log.debug("Adding URI to form " + existingURI);
//		
//	}
//
//	private String getExistingURIForGeography() {
//		
//	}
//
//	private String getSparqlQueryResult() {
//		String geographyURI = null;
//		String query = "SELECT ?geography WHERE {?geography <http://nyclimateclearinghouse.org/ontology/geometryIdentifier> '"
//				+ objectIdentifier
//				+ "' ."
//				+ "?geography <http://nyclimateclearinghouse.org/ontology/geometryType> '"
//				+ objectTypeString + "' .}";
//		log.debug("Query to be executed to check if this geometry already exists is "
//				+ query);
//
//		try {
//
//			ResultSet results = RDFServiceUtils.sparqlSelectQuery(query,
//					rdfService);
//			while (results.hasNext()) {
//				QuerySolution qs = results.nextSolution();
//				if (qs.get("geography") != null
//						&& qs.get("geography").isResource()) {
//
//					Resource geographyResource = qs.getResource("geography");
//					geographyURI = geographyResource.getURI();
//				}
//			}
//
//		} catch (Throwable t) {
//				log.error("Error in executing sparql query to retrieve any existing geographies with the same geometry type and uid");
//				log.error(t, t);
//		}
//
//		if (log.isDebugEnabled()) {
//			log.debug("query: '" + query + "'");
//
//		}
//
//		return geographyURI;
//	}
//
//	// Since we will change the uris and literals from form, we should make
//	// copies
//	// of the original values and store them, this will also make iterations
//	// and updates to the submission independent from accessing the values
//	private void copySubmissionValues() {
//		// Retrieve the geometry type and uid of the element added
//		Map<String, List<Literal>> literalsFromForm = submission
//				.getLiteralsFromForm();
//		Map<String, List<String>> transformed = EditConfigurationUtils
//				.transformLiteralMap(literalsFromForm);
//		String idKey = "objectIdentifier";
//		String typeKey = "objectTypeString";
//		objectIdentifier = getTransformedValue(transformed, idKey);
//		objectTypeString = getTransformedValue(transformed, typeKey);
//		
//	}
//
//	private String getTransformedValue(Map<String, List<String>> transformed,
//			String key) {
//		String value = null;
//		if (transformed.containsKey(key)) {
//			List<String> values = transformed.get(key);
//			if (values.size() > 0) {
//				value = transformed.get(key).get(0);
//			}
//		}
//		return value;
//	}
//
//	private Object getFirstElement(List inputList) {
//		if (inputList == null || inputList.size() == 0)
//			return null;
//		return inputList.get(0);
//	}
//
//}
