<#if qualAttDatasets?has_content>
  <article class="property" role="article">
    <h3 id="qualifiedAttribution" title="">
        qualifiedAttribution
        <img class="add-individual" src="/vivo/images/individual/addIcon.gif" alt="add"></img>
    </h3>
    <ul id="qualifiedAttribution-Attribution-List" class="property-list" role="list" displaylimit="5">
        <#list qualAttDatasets as resultRow>
            <li role="listitem">
                <a href="${urls.base}/individual?uri=${resultRow["datasetURI"]}" title="name">
                    ${resultRow["dlabel"]}
                </a>
            </li>
        </#list>
    </ul>   
  </article>
</#if>
