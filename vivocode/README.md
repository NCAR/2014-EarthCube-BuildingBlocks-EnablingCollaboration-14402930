# EarthCollab Crosslinking Code
Enables the lookup and display of external information on VIVO via the 'sameAs' property

## Building the application
The vivocode directory is equivalent to VIVO's 'installer' directory. You can place the vivocode directory next to VIVO and Vitro:
```
  .
  +--VIVO
  +--Vitro
  +--vivocode
```

  Edit or copy example-settings.xml in vivocode to set tomcat-dir and vivo-dir
  
  cd to the VIVO directory and build using this command:
  
  ```
  mvn install -s ../vivocode/example-settings.xml -Dvivo-installer-dir=../vivocode
  ```

Before you start Tomcat, be sure to edit runtime.properties and applicationSetup.n3 (if necessary) in the vivo-dir directory you specified in example-settings.xml.

## Configuration
1. Create a file called externalLookupServices.n3 in {vivo-dir}/rdf/abox/filegraph/externalLookupServices.n3
```
  # $This file is distributed under the terms of the license in /doc/license.txt$

  @prefix owl: <http://www.w3.org/2002/07/owl#> .
  @prefix display: <http://vitro.mannlib.cornell.edu/ontologies/display/1.1#> .
  @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  @prefix core: <http://vivoweb.org/ontology/core#> .
  @prefix vivoweb: <http://vivoweb.org/ontology#> .
  @prefix foaf: <http://xmlns.com/foaf/0.1/> .
  @prefix earthcollab: <http://vivo.earthcollab.edu/individual/> .


  #External server information
  earthcollab:testCornellSolrLookup a <java:edu.cornell.mannlib.vitro.webapp.search.externallookup.impl.SolrLookup>;
  a <java:edu.cornell.mannlib.vitro.webapp.search.externallookup.ExternalLookupService>;
  rdfs:label "External VIVO Lookup";
  earthcollab:hasSolrAPIURL "http://vivo.university.edu/vivosolr/collection1/select?";
  earthcollab:hasEndpointURL "http://vivo.university.edu/vivo";
  earthcollab:hasEndpointLabel "External VIVO" .
```
  
2. Go to http://{your.vivo}/propertyEdit?uri=http%3A%2F%2Fwww.w3.org%2F2002%2F07%2Fowl%23sameAs  
 Click edit property and ensure the custom entry form field is set to: edu.cornell.mannlib.vitro.webapp.edit.n3editing.configuration.generators.AddExternalEntityGenerator
  
3. Restart Tomcat