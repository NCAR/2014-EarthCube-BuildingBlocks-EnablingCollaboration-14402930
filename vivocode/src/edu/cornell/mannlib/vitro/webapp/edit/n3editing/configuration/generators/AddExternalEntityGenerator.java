/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.edit.n3editing.configuration.generators;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import javax.servlet.http.HttpSession;

import edu.cornell.mannlib.vitro.webapp.beans.VClass;
import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
import edu.cornell.mannlib.vitro.webapp.dao.VitroVocabulary;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationUtils;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.EditConfigurationVTwo;
import edu.cornell.mannlib.vitro.webapp.edit.n3editing.VTwo.fields.FieldVTwo;
import edu.cornell.mannlib.vitro.webapp.modules.searchEngine.SearchEngineException;


/**
 * Generic generator for linking to any external entity that has a URI
 *
 */

public class AddExternalEntityGenerator extends DefaultObjectPropertyFormGenerator {
	private String acObjectPropertyTemplate = "externalAutoCompleteObjectPropForm.ftl";		
	private String lookupServiceURI = "externalSolr";

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
				
		//Overriding template
		setTemplate(editConfig);
		//pass in service URI
		addFormSpecificDataForService(editConfig,vreq,session);
		//Add preprocessors - whatever might exist
	
		return editConfig;
	}
	
	
	private void setTemplate(EditConfigurationVTwo editConfiguration) {
		
		editConfiguration.setTemplate(acObjectPropertyTemplate);
	}
	
	//Form specific data used here to pass back the lookups associated with this property
	public void addFormSpecificDataForService(EditConfigurationVTwo editConfiguration, VitroRequest vreq, HttpSession session) throws SearchEngineException {
				editConfiguration.addFormSpecificData("serviceURI", lookupServiceURI);
		
	}
	
	//In addition to default n3 for object, add N3 for 
	//TODO: Check what about the following may need to be changed in case geography label changes
	 private List<String> addN3Required() {
    	List<String> n3ForEdit = new ArrayList<String>();
    
    	return n3ForEdit;
    }
	 
	 private List<String> addN3Optional() {
		 //Associate type and identifier with location
		 List<String> n3ForEdit = new ArrayList<String>();
		
		 return n3ForEdit;
	 }
	
	
	
	
	
}
