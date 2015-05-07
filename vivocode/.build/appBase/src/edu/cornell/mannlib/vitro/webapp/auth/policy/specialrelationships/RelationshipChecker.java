/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.auth.policy.specialrelationships;

import java.util.ArrayList;
import java.util.List;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import com.hp.hpl.jena.ontology.OntModel;
import com.hp.hpl.jena.rdf.model.Property;
import com.hp.hpl.jena.rdf.model.RDFNode;
import com.hp.hpl.jena.rdf.model.Resource;
import com.hp.hpl.jena.rdf.model.Selector;
import com.hp.hpl.jena.rdf.model.SimpleSelector;
import com.hp.hpl.jena.rdf.model.StmtIterator;
import com.hp.hpl.jena.shared.Lock;

import edu.cornell.mannlib.vitro.webapp.auth.policy.BasicPolicyDecision;
import edu.cornell.mannlib.vitro.webapp.auth.policy.ifaces.Authorization;
import edu.cornell.mannlib.vitro.webapp.auth.policy.ifaces.PolicyDecision;
import edu.cornell.mannlib.vitro.webapp.dao.VitroVocabulary;

/**
 * Look for relationships within an OntModel. Types of resources, links between
 * resources, and links between resources via a context node.
 * 
 * Also provides some convenience methods for test lists of URIs and for
 * creating PolicyDecisions.
 */
public class RelationshipChecker {
	private static final Log log = LogFactory.getLog(RelationshipChecker.class);

	protected static final String NS_CORE = "http://vivoweb.org/ontology/core#";
	protected static final String NS_OBO = "http://purl.obolibrary.org/obo/";
	protected static final String URI_RELATES = NS_CORE + "relates";
	protected static final String URI_RELATED_BY = NS_CORE + "relatedBy";
	protected static final String URI_INHERES_IN = NS_OBO + "RO_0000052";
	protected static final String URI_REALIZES = NS_OBO + "BFO_0000055";

	private final OntModel ontModel;

	public RelationshipChecker(OntModel ontModel) {
		this.ontModel = ontModel;
	}

	/**
	 * Are there any URIs that appear in both of these lists?
	 */
	public boolean anyUrisInCommon(List<String> list1, List<String> list2) {
		List<String> urisInCommon = new ArrayList<String>(list1);
		urisInCommon.retainAll(list2);
		return !urisInCommon.isEmpty();
	}

	/**
	 * Is this resource a member of this type? That is, is there an statement of
	 * the form: <resourceUri> rdfs:type <typeUri>
	 */
	public boolean isResourceOfType(String resourceUri, String typeUri) {
		Selector selector = createSelector(resourceUri,
				VitroVocabulary.RDF_TYPE, typeUri);

		StmtIterator stmts = null;
		ontModel.enterCriticalSection(Lock.READ);
		try {
			stmts = ontModel.listStatements(selector);
			if (stmts.hasNext()) {
				log.debug("resource '" + resourceUri + "' is of type '"
						+ typeUri + "'");
				return true;
			} else {
				log.debug("resource '" + resourceUri + "' is not of type '"
						+ typeUri + "'");
				return false;
			}
		} finally {
			if (stmts != null) {
				stmts.close();
			}
			ontModel.leaveCriticalSection();
		}
	}

	/**
	 * Get a list of the object URIs that satisfy this statement:
	 * 
	 * <resourceUri> <propertyUri> <objectUri>
	 * 
	 * May return an empty list, but never returns null.
	 */
	public List<String> getObjectsOfProperty(String resourceUri,
			String propertyUri) {
		List<String> list = new ArrayList<String>();

		Selector selector = createSelector(resourceUri, propertyUri, null);

		StmtIterator stmts = null;
		ontModel.enterCriticalSection(Lock.READ);
		try {
			stmts = ontModel.listStatements(selector);
			while (stmts.hasNext()) {
				list.add(stmts.next().getObject().toString());
			}
			log.debug("Objects of property '" + propertyUri + "' on resource '"
					+ resourceUri + "': " + list);
			return list;
		} finally {
			if (stmts != null) {
				stmts.close();
			}
			ontModel.leaveCriticalSection();
		}
	}

	/**
	 * Get a list of the object URIs that satisfy these statements:
	 * 
	 * <resourceUri> <linkUri> <contextNodeUri>
	 * 
	 * <contextNodeUri> <propertyUri> <objectUri>
	 * 
	 * May return an empty list, but never returns null.
	 */
	public List<String> getObjectsOfLinkedProperty(String resourceUri,
			String linkUri, String propertyUri) {
		List<String> list = new ArrayList<String>();

		Selector selector = createSelector(resourceUri, linkUri, null);

		StmtIterator stmts = null;

		ontModel.enterCriticalSection(Lock.READ);
		try {
			stmts = ontModel.listStatements(selector);
			while (stmts.hasNext()) {
				RDFNode contextNode = stmts.next().getObject();
				if (contextNode.isResource()) {
					log.debug("found context node for '" + resourceUri + "': "
							+ contextNode);
					list.addAll(getObjectsOfProperty(contextNode.asResource()
							.getURI(), propertyUri));
				}
			}
			log.debug("Objects of linked properties '" + linkUri + "' ==> '"
					+ propertyUri + "' on '" + resourceUri + "': " + list);
			return list;
		} finally {
			if (stmts != null) {
				stmts.close();
			}
			ontModel.leaveCriticalSection();
		}
	}

	/**
	 * Get a list of URIs for object that link to the specified resource, by
	 * means of the specified properties, through a linking node of the
	 * specified type.
	 * 
	 * So we're looking for object URIs that statisfy these statements:
	 * 
	 * <resourceUri> <property1Uri> <linkNodeUri>
	 * 
	 * <linkNodeUri> rdfs:type <linkNodeTypeUri>
	 * 
	 * <linkNodeUri> <property2Uri> <objectUri>
	 */
	public List<String> getObjectsThroughLinkingNode(String resourceUri,
			String property1Uri, String linkNodeTypeUri, String property2Uri) {
		List<String> list = new ArrayList<String>();

		for (String linkNodeUri : getObjectsOfProperty(resourceUri, property1Uri)) {
			if (isResourceOfType(linkNodeUri, linkNodeTypeUri)) {
				list.addAll(getObjectsOfProperty(linkNodeUri, property2Uri));
			}
		}
		
		return list;
	}

	public Selector createSelector(String subjectUri, String predicateUri,
			String objectUri) {
		Resource subject = (subjectUri == null) ? null : ontModel
				.getResource(subjectUri);
		return createSelector(subject, predicateUri, objectUri);
	}

	public Selector createSelector(Resource subject, String predicateUri,
			String objectUri) {
		Property predicate = (predicateUri == null) ? null : ontModel
				.getProperty(predicateUri);
		RDFNode object = (objectUri == null) ? null : ontModel
				.getResource(objectUri);
		return new SimpleSelector(subject, predicate, object);
	}

	/** An AUTHORIZED decision with a message like "PolicyClass: message". */
	protected PolicyDecision authorizedDecision(String message) {
		return new BasicPolicyDecision(Authorization.AUTHORIZED, getClass()
				.getSimpleName() + ": " + message);
	}

}
