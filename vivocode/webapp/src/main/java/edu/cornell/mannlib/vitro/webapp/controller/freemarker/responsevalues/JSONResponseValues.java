/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.controller.freemarker.responsevalues;

import net.sf.json.JSONObject;
import net.sf.json.JSONSerializer;

import org.apache.jena.rdf.model.Model;

import edu.cornell.mannlib.vitro.webapp.web.ContentType;

public class JSONResponseValues extends BaseResponseValues {

    //private JSONObject jsonObject;
    private String jsonString;
    public JSONResponseValues(ContentType contentType, String jsonString) {
        super(contentType);
        this.jsonString = jsonString;

    }

    public JSONResponseValues(ContentType contentType, String jsonString, int statusCode) {
        super(contentType, statusCode);
        this.jsonString = jsonString;

    }



    //Get values returned as JSON object
    public String getJSON() {
    	return this.jsonString;
    }
}
