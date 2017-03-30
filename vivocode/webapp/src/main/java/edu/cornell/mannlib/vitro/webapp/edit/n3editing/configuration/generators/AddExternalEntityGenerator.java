/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.edit.n3editing.configuration.generators;

import java.util.ArrayList;
import java.util.List;

import javax.servlet.http.HttpSession;

import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.Literal;
import org.apache.jena.rdf.model.Resource;

import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationVTwo;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.fields.FieldVTwo;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.configuration.preprocessors.ExternalEntityLookupSubmissionPreprocessor;
import edu.cornell.mannlib.vitro.webapp.modules.searchEngine.SearchEngineException;
import edu.cornell.mannlib.vitro.webapp.rdfservice.impl.RDFServiceUtils;


/**
 * Generic generator for linking to any external entity that has a URI
 *
 */

public class AddExternalEntityGenerator extends DefaultObjectPropertyFormGenerator {
	private String acObjectPropertyTemplate = "externalAutoCompleteObjectPropForm.ftl";

	@Override
	public EditConfigurationVTwo getEditConfiguration(VitroRequest vreq,
			HttpSession session) throws Exception {
		//force auto complete
		doAutoComplete = true;

		EditConfigurationVTwo editConfig= super.getEditConfiguration(vreq, session);

		editConfig.addN3Required(this.addN3Required());
		editConfig.addN3Optional(this.addN3Optional());

		//Enable URI to be created for this object, because linking to an external
		//object that may or may not already exist within the system
		editConfig.addNewResource("objectVar", null);
		editConfig.addNewResource("endpointURI", null);

		//Additional fields
		editConfig.addFields(getAdditionalFieldsOnForm());

		//Additional literals on form
		editConfig.addLiteralsOnForm(getAdditionalLiteralsOnForm());


		//Overriding template
		setTemplate(editConfig);
		//pass in service URI
		addFormSpecificDataForService(editConfig,vreq,session);
		//Add preprocessors - whatever might exist
		editConfig.addEditSubmissionPreprocessor(new ExternalEntityLookupSubmissionPreprocessor(editConfig));

		return editConfig;
	}


	private void setTemplate(EditConfigurationVTwo editConfiguration) {

		editConfiguration.setTemplate(acObjectPropertyTemplate);
	}

	//Form specific data used here to pass back the lookups associated with this property
	public void addFormSpecificDataForService(EditConfigurationVTwo editConfiguration, VitroRequest vreq, HttpSession session) throws SearchEngineException {
			List<ServiceInfo> serviceInfo = this.getServicesInfo(vreq);
			editConfiguration.addFormSpecificData("servicesInfo", serviceInfo);

	}
	List<ServiceInfo> getServicesInfo(VitroRequest vreq) {
		List<ServiceInfo> servicesInfo = new ArrayList<ServiceInfo>();
		//Execute sparql query to retrieve information about the available services
		String queryStr = "SELECT ?serviceURI ?serviceLabel WHERE {?serviceURI a <java:edu.cornell.mannlib.vitro.webapp.search.externallookup.ExternalLookupService> . ?serviceURI <http://www.w3.org/2000/01/rdf-schema#label> ?serviceLabel .}";
		ResultSet rs = RDFServiceUtils.sparqlSelectQuery(queryStr, vreq.getRDFService());
		while(rs.hasNext()) {
			String serviceURI = null;
			String serviceLabel = null;
			QuerySolution qs = rs.nextSolution();
			if(qs.get("serviceURI") != null && qs.get("serviceURI").isURIResource()) {
				Resource serviceURIResource = qs.getResource("serviceURI");
				serviceURI = serviceURIResource.getURI();
			}
			if(qs.get("serviceLabel") != null && qs.get("serviceLabel").isLiteral()) {
				Literal serviceLabelLiteral = qs.getLiteral("serviceLabel");
				serviceLabel = serviceLabelLiteral.getString();
			}
			servicesInfo.add(new ServiceInfo(serviceURI, serviceLabel));
		}
		return servicesInfo;
	}


	//In addition to default n3 for object, add N3 for
	//TODO: Check what about the following may need to be changed in case geography label changes
	 private List<String> addN3Required() {
    	List<String> n3ForEdit = new ArrayList<String>();
    	//Expect this information to be present but
    	n3ForEdit.add("?objectVar <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#ExternalEntity> . ");
    	n3ForEdit.add("?objectVar <http://vivoweb.org/ontology/core#externalServiceDefinition> ?endpointURI. ");
    	n3ForEdit.add("?endpointURI <http://vivoweb.org/ontology/core#externalURL>  ?endpointURL . ");
    	n3ForEdit.add("?endpointURI <http://www.w3.org/2000/01/rdf-schema#label>  ?endpointLabel . ");

    	return n3ForEdit;
    }

	 private List<String> addN3Optional() {
		 //Associate type and identifier with location
		 List<String> n3ForEdit = new ArrayList<String>();

		 return n3ForEdit;
	 }


	 private List<String> getAdditionalLiteralsOnForm() {
	    	List<String> literalsOnForm = new ArrayList<String>();
	    	literalsOnForm.add("endpointURL");
	    	literalsOnForm.add("endpointLabel");
	    	return literalsOnForm;
	 }

	 //Not sure what existing URIs can be returned
	 private List<String> getAdditionalURIsOnForm() {
		 List<String> urisOnForm = new ArrayList<String>();

		 return urisOnForm;
	 }


	 private List<FieldVTwo> getAdditionalFieldsOnForm() {
		 List<FieldVTwo> fields = new ArrayList<FieldVTwo>();
		 fields.add(new FieldVTwo().setName("endpointURL"));
		 fields.add(new FieldVTwo().setName("endpointLabel"));

		 return fields;
	 }


	 public class ServiceInfo {
		 /**
		 * @return the serviceURI
		 */
		public String getServiceURI() {
			return serviceURI;
		}
		/**
		 * @return the serviceLabel
		 */
		public String getServiceLabel() {
			return serviceLabel;
		}
		public ServiceInfo(String serviceURI, String serviceLabel) {
			super();
			this.serviceURI = serviceURI;
			this.serviceLabel = serviceLabel;
		}
		private String serviceURI;
		 private String serviceLabel;

	 }


}
