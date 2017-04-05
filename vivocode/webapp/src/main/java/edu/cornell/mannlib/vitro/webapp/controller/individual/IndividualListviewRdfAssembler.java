/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.controller.individual;

import java.io.StringWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.servlet.ServletContext;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.ontology.OntModel;
import org.apache.jena.ontology.OntModelSpec;
import org.apache.jena.rdf.model.Literal;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.NodeIterator;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.rdf.model.StmtIterator;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;

import edu.cornell.mannlib.vitro.webapp.auth.policy.PolicyHelper;
import edu.cornell.mannlib.vitro.webapp.auth.requestedAction.RequestedAction;
import edu.cornell.mannlib.vitro.webapp.auth.requestedAction.publish.PublishDataPropertyStatement;
import edu.cornell.mannlib.vitro.webapp.auth.requestedAction.publish.PublishObjectPropertyStatement;
import edu.cornell.mannlib.vitro.webapp.beans.DataPropertyStatement;
import edu.cornell.mannlib.vitro.webapp.beans.DataPropertyStatementImpl;
import edu.cornell.mannlib.vitro.webapp.beans.Individual;
import edu.cornell.mannlib.vitro.webapp.controller.VitroRequest;
import edu.cornell.mannlib.vitro.webapp.controller.freemarker.responsevalues.RdfResponseValues;
import edu.cornell.mannlib.vitro.webapp.controller.freemarker.responsevalues.ResponseValues;
import edu.cornell.mannlib.vitro.webapp.dao.VitroVocabulary;
import edu.cornell.mannlib.vitro.webapp.dao.WebappDaoFactory;
import edu.cornell.mannlib.vitro.webapp.rdfservice.RDFService;
import edu.cornell.mannlib.vitro.webapp.rdfservice.RDFServiceException;
import edu.cornell.mannlib.vitro.webapp.rdfservice.impl.RDFServiceUtils;
import edu.cornell.mannlib.vitro.webapp.utils.jena.ExtendedLinkedDataUtils;
import edu.cornell.mannlib.vitro.webapp.utils.jena.JenaOutputUtils;
import edu.cornell.mannlib.vitro.webapp.web.ContentType;
import edu.cornell.mannlib.vitro.webapp.web.beanswrappers.ReadOnlyBeansWrapper;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.GroupedPropertyList;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.IndividualTemplateModel;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.IndividualTemplateModelBuilder;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.ObjectPropertyTemplateModel;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.PropertyGroupTemplateModel;
import edu.cornell.mannlib.vitro.webapp.web.templatemodels.individual.PropertyTemplateModel;
import freemarker.template.TemplateModel;

/**
 * Return RDF from the list views associated with a profile
 */
public class IndividualListviewRdfAssembler {
	private static final Log log = LogFactory
			.getLog(IndividualRdfAssembler.class);

	private static final String RICH_EXPORT_ROOT = "/WEB-INF/rich-export/";
	private static final String INCLUDE_ALL = "all";

	private static final String NS_DC = "http://purl.org/dc/elements/1.1/";
	private static final String URI_RIGHTS = NS_DC + "rights";
	private static final String URI_DATE = NS_DC + "date";
	private static final String URI_PUBLISHER = NS_DC + "publisher";

	private static final String NS_FOAF = "http://xmlns.com/foaf/0.1/";
	private static final String URI_DOCUMENT = NS_FOAF + "Document";

	private static final String URI_LABEL = VitroVocabulary.RDFS + "label";
	private static final String URI_TYPE = VitroVocabulary.RDF_TYPE;

	private final VitroRequest vreq;
	private final ServletContext ctx;
	private final String individualUri;
	private final Individual individual;
	private final ContentType rdfFormat;
	private final String[] richExportIncludes;
	private final RDFService rdfService;
	private final OntModel contentModel;
	private final WebappDaoFactory wadf;

	public IndividualListviewRdfAssembler(VitroRequest vreq, Individual individual,
			ContentType rdfFormat) {
		this.vreq = vreq;
		this.ctx = vreq.getSession().getServletContext();
		this.individual = individual;
		this.individualUri = individual.getURI();
		this.rdfFormat = rdfFormat;
		String[] includes = vreq.getParameterValues("include");
		this.richExportIncludes = (includes == null) ? new String[0] : includes;

		if (isLanguageAware()) {
			this.rdfService = vreq.getRDFService();
			this.contentModel = vreq.getJenaOntModel();
		} else {
			this.rdfService = vreq.getUnfilteredRDFService();
			this.contentModel = vreq.getLanguageNeutralUnionFullModel();
		}

		wadf = vreq.getWebappDaoFactory();
	}

	public ResponseValues assembleRdf() {
		OntModel newModel = getRdf();
		//newModel.add(getRichExportRdf());
		JenaOutputUtils.setNameSpacePrefixes(newModel, wadf);
		return new RdfResponseValues(rdfFormat, newModel);
	}

	private boolean isLanguageAware() {
		return StringUtils.isNotEmpty(vreq.getHeader("Accept-Language"));
	}

	private OntModel getRdf() {
		OntModel o = ModelFactory.createOntologyModel(OntModelSpec.OWL_MEM);
		/*o.add(getStatementsAboutEntity());
		o.add(getLabelsAndTypesOfRelatedObjects());
		filterByPolicy(o);*/

		//Get list view metadata
		addListViewRDF(o);
		filterByPolicy(o);
		addDocumentMetadata(o);
		return o;
	}

	private void addListViewRDF(OntModel o) {

		IndividualTemplateModel itm = IndividualTemplateModelBuilder.build(individual, vreq);
        GroupedPropertyList gpl = itm.getPropertyList();
        //Return grouped property list as RDF
        o.add(gpl.getAllPropertiesAsRDF());
	}



	/**
	 * Add info about the RDF itself.
	 *
	 * It will look something like this:
	 *
	 * <pre>
	 * <http://vivo.cornell.edu/individual/n6628/n6628.rdf>
	 *     rdfs:label "RDF description of Baker, Able - http://vivo.cornell.edu/individual/n6628" ;
	 *     rdf:type foaf:Document ;
	 *     dc:publisher <http://vivo.cornell.edu> ;
	 *     dc:date "2007-07-13"^^xsd:date ;
	 *     dc:rights <http://vivo.cornell.edu/termsOfUse> .
	 * </pre>
	 */
	private void addDocumentMetadata(OntModel o) {
		String baseUrl = figureBaseUrl();
		String documentUri = createDocumentUri();
		String label = createDocumentLabel(o);
		Literal dateLiteral = createDateLiteral(o);

		Resource md = o.getResource(documentUri);

		o.add(md, o.getProperty(URI_LABEL), label);
		o.add(md, o.getProperty(URI_TYPE), o.getResource(URI_DOCUMENT));
		o.add(md, o.getProperty(URI_PUBLISHER), o.getResource(baseUrl));
		o.add(md, o.getProperty(URI_DATE), dateLiteral);
		o.add(md, o.getProperty(URI_RIGHTS),
				o.getResource(baseUrl + "/termsOfUse"));
	}

	private String figureBaseUrl() {
		int cutHere = individualUri.indexOf("/individual");
		return (cutHere > 0) ? individualUri.substring(0, cutHere)
				: individualUri;
	}

	private String createDocumentUri() {
		return vreq.getRequestURL().toString();
	}

	private String createDocumentLabel(OntModel o) {
		String label = null;
		NodeIterator nodes = o.listObjectsOfProperty(
				o.getResource(individualUri), o.getProperty(URI_LABEL));
		while (nodes.hasNext()) {
			RDFNode n = nodes.nextNode();
			if (n.isLiteral()) {
				label = n.asLiteral().getString();
			}
		}
		if (label == null) {
			return "RDF description of " + individualUri;
		} else {
			return "RDF description of " + label + " - " + individualUri;
		}
	}

	private Literal createDateLiteral(OntModel o) {
		String date = new SimpleDateFormat("YYYY-MM-dd'T'HH:mm:ss")
				.format(new Date());
		return o.createTypedLiteral(date, XSDDatatype.XSDdateTime);
	}

	//Borrowed from IndividualRdfAssembler - filter by policy
	/**
	 * Remove any triples that we aren't allowed to see. Then remove any objects
	 * that we no longer have access to.
	 */
	private void filterByPolicy(OntModel o) {
		Model removeModel = removeProhibitedTriples(o);

		Set<String> notOkObjects = determineInaccessibleUris(o, removeModel);
		removeOrphanedObjects(o, notOkObjects);
	}

	/**
	 * Remove the triples that we aren't allowed to see.
	 * Keep track of the triples removed in the model
	 */
	private Model removeProhibitedTriples(OntModel o) {
		StmtIterator stmts = o.listStatements();
		Model removeModel = ModelFactory.createDefaultModel();
		while (stmts.hasNext()) {
			Statement stmt = stmts.next();
			String subjectUri = stmt.getSubject().getURI();
			String predicateUri = stmt.getPredicate().getURI();
			if (stmt.getObject().isLiteral()) {
				String value = stmt.getObject().asLiteral().getString();
				DataPropertyStatement dps = new DataPropertyStatementImpl(
						subjectUri, predicateUri, value);
				RequestedAction pdps = new PublishDataPropertyStatement(o, dps);
				if (!PolicyHelper.isAuthorizedForActions(vreq, pdps)) {
					log.debug("not authorized: " + pdps);
					//stmts.remove();
					removeModel.add(stmt);
				}
			} else if (stmt.getObject().isURIResource()) {
				String objectUri = stmt.getObject().asResource().getURI();
				RequestedAction pops = new PublishObjectPropertyStatement(o,
						subjectUri, predicateUri, objectUri);
				if (!PolicyHelper.isAuthorizedForActions(vreq, pops)) {
					log.debug("not authorized: " + pops);
					//stmts.remove();
					removeModel.add(stmt);
				}
			} else {
				log.warn("blank node: " + stmt);
				stmts.remove(); //we will just remove blank nodes for now, should there be a need to preserve them, we can revisit this
			}
		}
		o.remove(removeModel);
		return removeModel;
	}

	/**
	 * Collect the URIs of all objects that are accessible through permitted
	 * triples.
	 */
	private Set<String> determineInaccessibleUris(OntModel o, Model removeModel) {

		Resource i = o.getResource(individualUri);
		Set<String> profileModelObjectUris = new HashSet<>();
		Set<String> inAccessibleUris = new HashSet<>();

		Set<RDFNode> profileObjects = o.listObjects().toSet();
		for(RDFNode n: profileObjects) {

			if(n.isURIResource()) {
				profileModelObjectUris.add(((Resource)n).getURI());
			}
		}
		//statements removed s p o, check if o is object of any other statement already in model
		//to see if linked in some other way as object from other statement
		NodeIterator it = removeModel.listObjects();

		while(it.hasNext()) {
			RDFNode objectNode = it.next();
			//Is this object from the statements that were removed also an object for some statement in the model after removal
			//i.e. is there some way to get to this object even after the other statement has been removed
			if(objectNode.isURIResource()) {
				String objectURI = ((Resource) objectNode).getURI();
				if(!profileModelObjectUris.contains(objectURI)) {
					inAccessibleUris.add(objectURI);
				}
			}
		}

		return inAccessibleUris;
	}

	/**
	 * Remove any statements about objects that cannot be reached through
	 * permitted triples, i.e. removed all statements that look like inaccessibleObject ?p ?o .
	 */
	private void removeOrphanedObjects(OntModel o, Set<String> notOkObjects) {
		for(String uri: notOkObjects) {
			StmtIterator stmts = o.listStatements(ResourceFactory.createResource(uri), null, (RDFNode) null);
			while (stmts.hasNext()) {
				Statement stmt = stmts.next();
				log.debug("removing orphan triple: " + stmt);
				stmts.remove();
			}
		}


	}

}
