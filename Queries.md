# Queries and Answers

This file serves the collectiom of the Neo4j queries which help you analyse the current state and quality of your wazuh rule set. 
>[!NOTE]
> the purpose of this collection is to give you all of the necessary tools and pointers of how to find out the things you need to know about. while most of the queries work out-of-the-box, you're *strongly encouraged* to play around and adjust the queries for your needs. 

## Delete all Queries

the following commands help you reset the database when you're testing different rule sets. 

- `docker compose down -v` (reset the docker container - preferred)
- `match (n) detach delete n ;` (neo4j equivalent of (drop all tables ))

## Querying Rules by Level:


```

match (n:Rule) where toInteger(n.level) > 10 return n.rule_id, n.description, n.level ;

```

## Visualizing rules as tree 
Most of the queries below just return a set of rules without their relations which can make navigating the result set difficult. You can append this Neo4j snippet 

```
MATCH path = (r)<-[:DEPENDS_ON*0..]-(:Rule)
RETURN path;
```

to get a the tree-like visualization of your rules. Here `r` is your ruleset you want to get.  


## Querying Rules from a Group
You need to 'attach' the following expression to any rule node that belongs to a group:

```

(g:Group {name:'fortimail'})-- <RULE>

```

For example, if you want all rules with level > 10 that belong to the `fortimail` group, the following query helps:
```

Match (g:Group {name:'fortimail'})--(n:Rule)
where toInteger(n.level) > 10
return n ;

```

Then, to visualize all rules of a group as a tree, just run this!

```
Match (g:Group {name:'fortimail'})--(r:Rule)
MATCH path = (r)<-[:DEPENDS_ON*0..]-(:Rule)
RETURN path;
```
## Searching for events
To find which rules are triggered under a given condition, use this query: 

```
match (r :Rule ) 
with r, [k IN keys(r) WHERE NOT k IN ['parents', 'level', 'rule_id', 'description', 'source_file']] AS field_keys
WITH r, [k IN field_keys | k + ': ' + toString(r[k])] AS field_kv_pairs
with r, apoc.text.join(field_kv_pairs, ' | ') AS field_string
where field_string contains "condition" 
return r, field_string; 

```
There you need to adjust the `condition` string. 

### Viewing chains 
If you want to see all rules affected by a certain condition, **including the children** use this query: 

```
match p=(r :Rule)<-[:DEPENDS_ON*]-(c:Rule) 
with p,r, [k IN keys(r) WHERE NOT k IN ['parents', 'level', 'rule_id', 'description', 'source_file']] AS field_keys
WITH p,r, [k IN field_keys | k + ': ' + toString(r[k])] AS field_kv_pairs
with p,r, apoc.text.join(field_kv_pairs, ' | ') AS field_string
where field_string contains "condition" 
return p, field_string; 

```


## Cyclic dependency
Rules which depend on themselves or build a cycle. 

```
MATCH (s:Rule)-[:DEPENDS_ON*]->(r:Rule)
where s.rule_id = r.rule_id
return s

```


## Orphaned Children
Rules that declare parents (in the `if_sid` or `if_matched_sid` attributes) but where those parents are not defined.

```

MATCH (child:Rule)
WHERE child.parents IS NOT NULL
AND NOT any(parent IN child.parents WHERE EXISTS {
MATCH (p:Rule {rule_id: parent})
})
RETURN child

```

Output missing parent rules along with their corresponding child:
```

MATCH (child:Rule)
WHERE child.parents IS NOT NULL
UNWIND child.parents AS parent
WITH child, parent
WHERE NOT EXISTS {
MATCH (p:Rule {rule_id: parent})
}
RETURN DISTINCT child, parent as missing_parent

```

<details>
<summary>Testing/Replication</summary>
This (invalid) rule creates the above state:

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

Just drop this rule in any xml rules file and run the query.

</details>

## Duplicate Rule IDs

Rules with the same ID that **do not override** each other (`override=yes` is not set).

```
MATCH (rule:Rule), (rule_duplicate:Rule) 
WHERE rule.rule_id = rule_duplicate.rule_id and 
not elementId(rule) = elementId(rule_duplicate) AND 
NOT (rule)-[:OVERWRITES]-(rule_duplicate) 
RETURN rule.rule_id, rule.source_file, rule_duplicate.source_file
```

## Children > Parents

Which **parents** have a smaller rule ID than their **children**?

```
Match (n:Rule) -[:DEPENDS_ON]-> (r:Rule) 
where toInteger(n.level) > toInteger(r.level) 
return n ; 
```

⚠️ WARNING: This returns a lot of results. You'll need additional predicates to navigate this properly.

## Rule source labeling
It is useful to differentiate the rules by their origin if you want to compare the rules provided by Wazuh with your custom rules. Here, we use the first part of the file path you provided with the -x parameter as the source label. Then we also take the overwrite attribute into account -> if the rule is overwritten, we do not consider it in our analysis. If it's different in your case, change or remove that expression. 

this code snippet can be appended to your query to get the source of the rule 

```
WITH replace(r.source_file, 'file://import/', '') AS trimmed
WITH split(trimmed, '/') AS parts
with parts[0] as source
```

Then, if you want to count how many rules are present in each ruleset, just run this: 

```
match (r:Rule) where r.overwrite is null
WITH replace(r.source_file, 'file://import/', '') AS trimmed, r
WITH split(trimmed, '/') AS parts, r
with parts[0] as source, r
return count(r), source ;
```

## Rule ID Distribution

Show the distribution of the rule ID allocation by different rule sources.

```
MATCH (r:Rule)
WHERE toInteger(r.rule_id) >= 0 AND toInteger(r.rule_id) <= 1000000 and r.overwrite is null
WITH toInteger(toInteger(r.rule_id) / 10000) AS bucket,r
WITH replace(r.source_file, 'file://import/', '') AS trimmed, bucket
WITH split(trimmed, '/') AS parts, bucket
with parts[0] as source, bucket
RETURN bucket * 10000 AS bucket_start,
       (bucket + 1) * 10000 - 1 AS bucket_end,
       source,
       count(*) AS rule_count
ORDER BY bucket_start, source;
```

<details>
<summary>Output: </summary>

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

## Trigger Chain of a Rule

Sometimes it's interesting to see which events trigger a rule. Generally, all predecessors (parents, ...) must be triggered first, then the rule itself. The following query gives the chain of predicates along with all conditions:

```
MATCH p = (:Rule {rule_id: "rule_id"})-[:DEPENDS_ON*]->(r:Rule)
where r.overwrite is null
WITH nodes(p) AS rules
UNWIND rules AS r
WITH DISTINCT r, [k IN keys(r) WHERE NOT k IN ['parents', 'level', 'rule_id', 'description', 'source_file']] AS field_keys
WITH r, [k IN field_keys | k + ': ' + toString(r[k])] AS field_kv_pairs
RETURN r.rule_id AS rule_id, r.description, apoc.text.join(field_kv_pairs, ' | ') AS field_string
```

<details>
<summary>Output:</summary> 
Rule_id = 101527
</details>

## Triggering Multiple Rules

For exploratory analysis, it's helpful to see the trigger chain of **multiple** rules at once. For example, if you want to see the chain of all rules with `level > 12`, this query helps:

```
MATCH p = (s:Rule)-[:DEPENDS_ON*0..]->(r:Rule)
where toInteger(s.level) > 12 and r.overwrite is null
WITH collect(r) AS rules, s
UNWIND rules AS r
WITH [k IN keys(r) 
    WHERE NOT k IN ['parents', 'level', 'rule_id', 'description', 'source_file']] AS field_keys, r, s
    WITH r, [k IN field_keys | k + ': ' + toString(r[k])] AS field_kv_pairs, s
WITH collect(field_kv_pairs) AS all_field_kv_pairs, s
WITH apoc.coll.flatten(all_field_kv_pairs) AS flat_fields, s
RETURN s.rule_id, apoc.text.join(flat_fields, ' | ') AS full_chain_fields;
```

<details>
<summary>Output:</summary>
...
</details>

## Competing Rules

Competing (sibling) rules are those triggered under the **same conditions**. That means rules that are based on the same parent but have identical predicates. Here’s the query:

```
MATCH (parent:Rule)<-[:DEPENDS_ON]-(child:Rule)
OPTIONAL MATCH (child)-[:BELONGS]->(g:Group)
WITH parent, child, collect(DISTINCT g) AS groupSet,
     [k IN keys(child) 
      WHERE NOT k IN ['parents', 'level', 'rule_id', 'description', 'source_file']] AS field_keys
WITH parent, child, groupSet,
     [k IN field_keys | k + ': ' + toString(child[k])] AS field_kv_pairs
WITH parent, apoc.text.join(field_kv_pairs, ' | ') AS condition_signature, child, groupSet
WITH parent, condition_signature, groupSet, collect(child.rule_id) AS equivalent_children
WHERE size(equivalent_children) > 1
RETURN parent.rule_id, parent.source_file, equivalent_children, condition_signature
ORDER BY parent.rule_id;

```
