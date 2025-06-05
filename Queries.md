# Queries and Answers

Hier nochmal alle gewünschten Abfragen. Separate Datei für die Übersicht 

## Löschen von allen Queries
- `docker compose down -v` (bevorzugt)
- `match (n) detach delete n ;`

## Regeln mit Level aufrufen: 

toInteger ist _manchmal_ notwendig...

```
match (n:Rule) where toInteger(n.level) > 10 return n.id, n.description, n.level ; 

```

## Regeln aus einer Gruppe aufrufen 
Folgender Ausdruck muss an die Regel die zur Gruppe gehören soll angehängt werden: 

```
(g:Group {name:'fortimail'})-- <REGEL>
```

Zum Beispiel: wenn wir alle regeln mit level > 10 die zur fortimail group gehören haben wollen, dann hilft uns die folgende query: 
```
Match (g:Group {name:'fortimail'})--(n:Rule)
where toInteger(n.level) > 10 
return n ; 
```



## Orphaned children
Regeln, dessen Parent (if_sid oder if_matched_sid) deklariert, aber nicht definiert ist.  

```
MATCH (n:Rule)
WHERE n.parent IS NOT NULL
AND NOT EXISTS {
  MATCH (r:Rule)
  WHERE r.id = n.parent
}
RETURN n
```
<details>
<summary>Testing/Replizieren</summary>
Diese (ungültige) Regel erzeugt diesen Zustand: 


```
  <rule id="8960099" level="5">
          <if_sid>57190</if_sid>
    <decoded_as>macOS_tccd</decoded_as>
    <match type="pcre2">(?i)update access record.+allowed</match>
  <rule id="89600" level="5">
    <decoded_as>macOS_tccd</decoded_as>
    <match type="pcre2">(?i)update access record.+allowed</match>
    <description>$(application) has been granted permission to $(service) at $(time).</description>
    <mitre>
      <id>T1222.002</id>
    </mitre>
    <group>pci_dss_10.6.1,gdpr_IV_35.7.d,hipaa_164.312.b,nist_800_53_AU.6,tsc_CC7.2,tsc_CC7.3,</group>
  </rule>
    <description>$(application) has been granted permission to $(service) at $(time).</description>
    <mitre>
      <id>T1222.002</id>
    </mitre>
    <group>pci_dss_10.6.1,gdpr_IV_35.7.d,hipaa_164.312.b,nist_800_53_AU.6,tsc_CC7.2,tsc_CC7.3,</group>
  </rule>
```



diese regel einfach irgendwo einfügen und die query ausführen
</details>


## Doppelt-vergebene IDs
Regeln die dieselbe ID haben, aber sich NICHT ÜBERSCHREIBEN (override=yes ist nicht gesetzt) 

```
MATCH (rule:Rule), (rule_duplicate:Rule) 
WHERE rule.id = rule_duplicate.id and 
not elementId(rule) = elementId(rule_duplicate) AND 
NOT (rule)-[:OVERWRITES]-(rule_duplicate) 
RETURN rule.id, rule.source_file, rule_duplicate.source_file
```

## Kinder > Eltern 
Welche ELTERN haben die kleinere Rule ID als ihre KINDER 

```
Match (n:Rule) -[:DEPENDS_ON]-> (r:Rule) 
where toInteger(n.level) > toInteger(r.level) 
return n ; 
```

WARNUNG: es sind sehr viele. es sind weitere prädikate notwendig um sich dort zurechtzufiden

### Verletzung des Schemas
Im Umkehrfall (also wo ELTERN > KIND) sind es auch sehr viele. Beispiel: 109180

> HIER MUSS DIE SPITZE KLAMMER UMGEDREHT WERDEN

## Regeln der Digifors
Folgendes Prädikat gibt die Digifors Regeln aus (Quelle: Kai)
`r.source_file CONTAINS "digifors" and r.overwrite is null`

In einfacher Sprache: der Dateiname beinhaltet "DIGIFORS" und die Regel ist nicht überschrieben. 

Ob die Overwrite Property über die Herkunft der Regel entscheidet, ist eine philosophische Frage, die jeder für sich selbst beantworten soll. Im Zweifelsfall kann dieses Prädikat einfach verallgemeinert werden: `r.source_file CONTAINS "digifors"` und in folgenden Queries angepasst werden. 

## Verteilung von IDs
Wie viele Digifors/Wazuh Regeln (sehe letzter Abschnitt) gibt es in den jeweiligen 10_000-er Blöcken. 
```
MATCH (r:Rule)
WHERE toInteger(r.id) >= 0 AND toInteger(r.id) <= 1000000
WITH toInteger(toInteger(r.id) / 10000) AS bucket,
     CASE WHEN r.source_file CONTAINS "digifors" and r.overwrite is null THEN "digifors" ELSE "wazuh" END AS rule_type
RETURN bucket * 10000 AS bucket_start,
       (bucket + 1) * 10000 - 1 AS bucket_end,
       rule_type,
       count(*) AS rule_count
ORDER BY bucket_start, rule_type;
```

<details>


<summary>Ausgabe: </summary>


```
╒════════════╤══════════╤══════════╤══════════╕
│bucket_start│bucket_end│rule_type │rule_count│
╞════════════╪══════════╪══════════╪══════════╡
...
├────────────┼──────────┼──────────┼──────────┤
│80000       │89999     │"wazuh"   │637       │
├────────────┼──────────┼──────────┼──────────┤
│90000       │99999     │"wazuh"   │967       │
├────────────┼──────────┼──────────┼──────────┤
│100000      │109999    │"digifors"│1012      │
├────────────┼──────────┼──────────┼──────────┤
...
├────────────┼──────────┼──────────┼──────────┤
│500000      │509999    │"wazuh"   │6         │
└────────────┴──────────┴──────────┴──────────┘

```

</details>

## Trigger-Kette einer Regel 

Es ist manchmal interessant zu wissen welche Ereignisse zum Triggern einer Regel führen. Im allg., müssen alle Vorgänger (Eltern, ...) der Regel getriggert werden, und dann sie selbst. Die folgende Query gibt diese Kette sowie alle `Field`-Attribute aus: 


Natürlich muss das ID angepasst werden

```
MATCH p = (:Rule {id: "101527"})-[:DEPENDS_ON*]->(r:Rule)
WITH nodes(p) AS rules
UNWIND rules AS r
WITH DISTINCT r, 
     [key IN keys(r) WHERE key STARTS WITH 'Field' | key + ': ' + toString(r[key])] +
     // also include 'match' if it exists
     CASE WHEN r.match is not null THEN ['match: ' + toString(r.match)] ELSE [] END AS field_kv_pairs
RETURN r.id AS rule_id, r.description, apoc.text.join(field_kv_pairs, ' | ') AS field_string;

```
 
<details>
<summary>Ausgabe:</summary> 

```
╒════════╤═════════════════════════════════════════════════════╤════════════════════════════════════════════════════╕
│rule_id │r.description                                        │field_string                                        │
╞════════╪═════════════════════════════════════════════════════╪════════════════════════════════════════════════════╡
│"101527"│"Checkpoint SmartDefense $(attack) by $(attack_info)"│"Field: attack_info: ^Command Injection Over HTTP.*"│
├────────┼─────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│"101526"│"Checkpoint SmartDefense $(attack) by $(attack_info)"│"Field: attack: ^Web Server Enforcement Violation$" │
├────────┼─────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│"101521"│"Checkpoint SmartDefense $(attack) $(attack_info)"   │"Field: fw_action: ^Detect$"                        │
├────────┼─────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│"101520"│"Checkpoint SmartDefense generic Event"              │"Field: product: ^SmartDefense$"                    │
├────────┼─────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│"64220" │"Checkpoint events."                                 │""                                                  │
├────────┼─────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│"64220" │"Checkpoint events."                                 │""                                                  │
└────────┴─────────────────────────────────────────────────────┴────────────────────────────────────────────────────┘

```

</details>

## Triggern mehrerer Regeln

für explorative analysen, ist es sinnvoll die trigger-kette mehrer regeln auf einmal zu sehen. also wenn wir die kette aller regeln mit level > 12 sehen wollen, hilft uns die folgende abfrage: 

```
MATCH p = (s:Rule)-[:DEPENDS_ON*0..]->(r:Rule)
where toInteger(s.level) > 12
WITH collect(r) AS rules, s
UNWIND rules AS r
WITH [key IN keys(r) WHERE key STARTS WITH 'Field' | key + ': ' + toString(r[key])] +
     // also include 'match' if it exists
     CASE WHEN r.match is not null THEN ['match: ' + toString(r.match)] ELSE [] END AS field_kv_pairs, s
WITH collect(field_kv_pairs) AS all_field_kv_pairs, s
WITH apoc.coll.flatten(all_field_kv_pairs) AS flat_fields, s
RETURN s.id, apoc.text.join(flat_fields, ' | ') AS full_chain_fields;

```

für andere konkrete fragenstellungen muss das prädikat einfach angepasst werden :)

<details>
<summary>ausgabe: </summary>


```
╒════════╤══════════════════════════════════════════════════════════════════════╕
│s.id    │full_chain_fields                                                     │
╞════════╪══════════════════════════════════════════════════════════════════════╡
│"92104" │"Field: win.eventdata.image: (*UTF)\N{U+202E}"                        │
├────────┼──────────────────────────────────────────────────────────────────────┤
│"92109" │"Field: win.eventdata.sourceIp: 0:0:0:0:0:0:0:1|127\.0\.0\.1 | Field: │
│        │win.eventdata.destinationIp: 0:0:0:0:0:0:0:1|127\.0\.0\.1 | Field: win│
│        │.eventdata.destinationPort: ^3389$ | Field: win.eventdata.destinationP│
│        │ort: ^3389$"                                                          │
├────────┼──────────────────────────────────────────────────────────────────────┤
│"5707"  │""                                                                    │
├────────┼──────────────────────────────────────────────────────────────────────┤
│"5714"  │""                                                                    │
├────────┼──────────────────────────────────────────────────────────────────────┤

```

</details>


<details>
<summary>Kai's Extra Felder</summary>

Kai möchte diese Ausgabe, aber noch mit LEVEL und rule owner. folgende query liefert diesen datensatz:

```
MATCH p = (s:Rule)-[:DEPENDS_ON*0..]->(r:Rule)
WHERE toInteger(s.level) > 10
WITH s, r,
     CASE WHEN r.source_file CONTAINS "digifors" AND r.overwrite IS NULL THEN 'digifors' ELSE 'wazuh' END AS owner,
     [key IN keys(r) WHERE key STARTS WITH 'Field' | key + ': ' + toString(r[key])] +
     // also include 'match' if it exists
     CASE WHEN r.match is not null THEN ['match: ' + toString(r.match)] ELSE [] END AS field_kv_pairs
WITH s, owner, collect(field_kv_pairs) AS r_field_data
WITH s, owner, apoc.coll.flatten(r_field_data) AS flat_fields
RETURN 
  s.id AS root_rule_id,
  s.level AS level,
  owner AS rule_owner,
  apoc.text.join(flat_fields, ' | ') AS full_chain_fields
ORDER BY root_rule_id, rule_owner;


```

Ausgabe: 

```
╒═════════╤══════════════════════════════════════════╤══════════════════════════════════════════╕
│parent_id│condition_signature                       │equivalent_children                       │
╞═════════╪══════════════════════════════════════════╪══════════════════════════════════════════╡
│"100021" │"Field: apex.cn3: 4 | Field: apex.cn2: 1 |│["100023", "100026"]                      │
│         │ match: Device Access Control"            │                                          │
├─────────┼──────────────────────────────────────────┼──────────────────────────────────────────┤
│"100901" │""                                        │["100902", "100903"]                      │
├─────────┼──────────────────────────────────────────┼──────────────────────────────────────────┤
```

aktuell fehlen noch die MATCH felder, aber das kommt noch ;)


</details>


## Konkurrierende Regeln 

Konkurrierende (Geschwister) Regeln sind die, die unter der selben Bedingungen (HIER: FIELD ATTRIBUTE) getriggert werden. Also welche Regeln die auf den selben Regeln basieren, aber gleiche Prädikate haben. Hier die Query:


```
MATCH (parent:Rule)<-[:DEPENDS_ON]-(child:Rule)
WITH parent, child,
     [key IN keys(child) WHERE key STARTS WITH 'Field' | key + ': ' + toString(child[key])] AS field_kv_pairs
WITH parent, apoc.text.join(field_kv_pairs, ' | ') AS condition_signature, child
WITH parent.id AS parent_id, condition_signature, collect(child.id) AS equivalent_children
WHERE size(equivalent_children) > 1
RETURN parent_id, condition_signature, equivalent_children
ORDER BY parent_id;

```

<details>
<summary>Ausgabe mit Beispiel</summary>

Ausgabe: 
```
╒═════════╤═════════════════════════════════════════════╤═════════════════════════════════════════════╕
│parent_id│condition_signature                          │equivalent_children                          │
╞═════════╪═════════════════════════════════════════════╪═════════════════════════════════════════════╡
│"100021" │"Field: apex.cn2: 1 | Field: apex.cn3: 4"    │["100023", "100026"]                         │
├─────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│"1002"   │""                                           │["51533", "51535", "1009", "2942", "3752"]   │
├─────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│"100901" │""                                           │["100902", "100903"]                         │
├─────────┼─────────────────────────────────────────────┼─────────────────────────────────────────────┤

```

Die erste Regel 100021 ist unter  9002-digifors_trendmicro-apexone.rules.xml

die beiden regeln sind so definiert: 

```
  <rule id="100026" level="9">
    <if_sid>100021</if_sid>
    <match>Device Access Control</match>
    <field name="apex.cn2">1</field>
    <field name="apex.cn3">4</field>
    <decoded_as>trend-micro</decoded_as>
    <description>Trend-Micro ApexOne: non-storage USB device blocked</description>
</rule>

  <rule id="100023" level="9">
      <if_sid>100021</if_sid>
      <match>Device Access Control</match>
      <field name="apex.cn2">1</field>
      <field name="apex.cn3">4</field>
      <decoded_as>trend-micro</decoded_as>
      <description>Trend-Micro ApexOne: non-storage USB device blocked</description>
  </rule>


```

</details>


