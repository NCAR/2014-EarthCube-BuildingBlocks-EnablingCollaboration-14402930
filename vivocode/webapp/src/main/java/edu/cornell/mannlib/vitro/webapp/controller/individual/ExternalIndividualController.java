/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.controller.individual;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.StringWriter;
import java.net.URL;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import net.sf.json.JSONArray;
import net.sf.json.JSONObject;
import net.sf.json.JSONSerializer;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
import edu.cornell.mannlib.vitro.webapp.controller.freemarker.FreemarkerHttpServlet;
import edu.cornell.mannlib.vitro.webapp.controller.freemarker.responsevalues.ExceptionResponseValues;
import edu.cornell.mannlib.vitro.webapp.controller.freemarker.responsevalues.JSONResponseValues;
import edu.cornell.mannlib.vitro.webapp.controller.freemarker.responsevalues.ResponseValues;
import edu.cornell.mannlib.vitro.webapp.web.ContentType;
import edu.cornell.mannlib.vitro.webapp.web.beanswrappers.ReadOnlyBeansWrapper;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.GroupedPropertyList;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.IndividualTemplateModel;
import freemarker.template.TemplateModel;
import freemarker.template.TemplateModelException;

/**
 * Handles requests for entity information.
 */
public class ExternalIndividualController extends FreemarkerHttpServlet {
	private static final Log log = LogFactory
			.getLog(ExternalIndividualController.class);

	private static final String TEMPLATE_HELP = "individual-help.ftl";


	@Override
	protected ResponseValues processRequest(VitroRequest vreq) {
		try {
			//Get the parameters for serviceURL and get the response

			String serviceURL = vreq.getParameter("serviceURL");
			String properties = vreq.getParameter("properties");
			String propertiesLength = vreq.getParameter("propertiesLength");
			int pLength = new Integer(propertiesLength).intValue();
			//Parameters in format properties[0][domainURI], etc.
			JSONArray propertiesJSON = (JSONArray) JSONSerializer.toJSON(properties);

			return assembleJSONResponse(serviceURL, propertiesJSON);
		} catch (Throwable e) {
			log.error(e, e);
			return new ExceptionResponseValues(e);
		}
	}


	@Override
	public void doPost(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		doGet(request, response);
	}

	ResponseValues assembleJSONResponse(String serviceURL, JSONArray propertiesJSON) throws TemplateModelException {


		try {
			String jsonString = "";
			JSONObject jsonObject = this.getExternalInfoFromService(serviceURL, propertiesJSON);
			JSONResponseValues jr = new JSONResponseValues(ContentType.JSON, jsonObject.toString());
			return jr;
		} catch (Exception e) {
			// TODO Auto-generated catch block
			log.error("An error occurred in rendering conceptInfo as json ", e);
			return null;
		}
	}

	JSONObject getExternalInfoFromService(String serviceURL, JSONArray propertiesJSON) {
		JSONObject jsonObject = null;
		String results = null;

		try {

			StringWriter sw = new StringWriter();
			URL rss = new URL(serviceURL);

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

			jsonObject = extractInfoAsJSON(results, propertiesJSON);


		} catch (Exception ex) {
			log.error("Exception occurred in retrieving results",ex);
			//ex.printStackTrace();
		}
		return jsonObject;
	}


	private JSONObject extractInfoAsJSON(String results,  JSONArray propertiesJSON) {
		JSONObject returnJSON = null;
		try {
			JSONObject resultsJSON = (JSONObject) JSONSerializer.toJSON(results);
			returnJSON = new JSONObject();
			int plength = propertiesJSON.size();
			int p;
			for(p = 0; p < plength; p ++) {
				JSONObject propertyInfo = propertiesJSON.getJSONObject(p);
				if(propertyInfo.containsKey("propertyURI")) {
					String propertyURI =  propertyInfo.getString("propertyURI");
					String propertyKey = propertyURI;
					//For publications, need "http://vivoweb.org/ontology/core#relatedBy-http://xmlns.com/foaf/0.1/Person-http://vivoweb.org/ontology/core#Authorship"
					if(propertyInfo.containsKey("domainURI") && propertyInfo.containsKey("rangeURI")
							&& StringUtils.isNotEmpty(propertyInfo.getString("domainURI"))
							&& StringUtils.isNotEmpty(propertyInfo.getString("rangeURI"))
							) {
						String domainURI = propertyInfo.getString("domainURI");
						String rangeURI = propertyInfo.getString("rangeURI");
						propertyKey = propertyURI + "-" + domainURI + "-" + rangeURI;
					}
					//Utilize propertyHash
					//Path - results.parsedList.propertyHash
					//TODO: Include check to see that this exists
					JSONObject propHash = resultsJSON.getJSONObject("parsedList").getJSONObject("propertyHash");
					JSONObject propInfo = propHash.getJSONObject(propertyKey);
					returnJSON.put(propertyKey, propInfo);
					//returnJSON = propInfo;
				} else {
					returnJSON = resultsJSON;
				}
			}

		} catch(Exception ex) {
			log.error("Error occurred in parsing results");
		}

		return returnJSON;
	}

}
