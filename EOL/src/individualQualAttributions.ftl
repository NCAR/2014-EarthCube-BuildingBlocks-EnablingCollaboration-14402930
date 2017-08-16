<#if qualAttDatasets?has_content>

  <article class="property" role="article">

    <h3 id="qualifiedAttribution" title="">
        qualifiedAttribution
        <img class="add-individual" src="/vivo/images/individual/addIcon.gif" alt="add"></img>
    </h3>

    <ul id="qualifiedAttribution-Attribution-List" class="property-list" role="list" displaylimit="5">

        <#assign first_time=0>
        <#assign last_dataset_uri="empty">

        <#compress>
        <#list qualAttDatasets as resultRow>
            <#assign this_dataset_uri><#t>
                ${resultRow["dataset"]}<#t>
            </#assign><#t>
            <#assign this_dataset_uri_trm=this_dataset_uri?trim><#t>                                      
                <#if first_time==0><#t>
                    <li role="listitem"><#t>
                        <a href="${urls.base}/individual?uri=${resultRow["dataset"]}"title="name"> ${resultRow["dname"]}</a>  ${resultRow["typeString"]}  (${resultRow["roleLabel"]?trim}<#t>
                <#elseif first_time==1 && this_dataset_uri_trm?string!=last_dataset_uri_trm?string><#t>
                    )</li><#t>
                    <li role="listitem"><#t>
                        <a href="${urls.base}/individual?uri=${resultRow["dataset"]}"title="name"> ${resultRow["dname"]}</a>  ${resultRow["typeString"]}  (${resultRow["roleLabel"]?trim}<#t>
                <#elseif first_time==1 && this_dataset_uri_trm?string==last_dataset_uri_trm?string><#t>
                    , ${resultRow["roleLabel"]?trim}<#t>
                </#if><#t>
                <#assign last_dataset_uri><#t>
                    ${resultRow["dataset"]}<#t>
                </#assign><#t>
                <#assign last_dataset_uri_trm=last_dataset_uri?trim><#t>
                <#assign first_time=1><#t>
        </#list>)</li><#t>
        </#compress>
    </ul>
  </article>
</#if>
