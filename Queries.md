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



