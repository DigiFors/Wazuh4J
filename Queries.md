# Queries and Answers

Hier nochmal alle gewünschten Abfragen. Separate Datei für die Übersicht 

## Löschen von allen Queries
- `docker compose down -v` (bevorzugt)
- `match (n) detach delete n ;`

## Regeln mit best. Level aufrufen: 

toInteger ist _manchmal_ notwendig...

```
match (n:Rule) where toInteger(n.level) > 10 return n.id, n.description, n.level ; 

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

Ausgabe: 
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



