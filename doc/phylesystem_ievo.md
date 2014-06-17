
# Using a git-based datastore for community curated phylogenies 
<br><br>

Emily Jane McTavish and Mark T. Holder  
University of Kansas  
iEvoBio, June 2014  

<img src="OpenTree-final.png" />

.notes: Pressing 2 will display these fascinating notes

.fx: titleslide


# presenter notes
Notes go here
---

# Open Tree of Life

<img src="OpenTree.jpg" />

.fx: imageslide whiteheading

---
# The data set
## Community contributed phylogenies

 - 6745 trees from 2914 published studies
 - 1188 trees from 991 studies partly curated 
 - 335 trees from 327 studies completely curated and included in the synthetic tree.


---
# The problem!
 - Large data set!
 - Thousands of phylogenies, and always growing (hopefully!)
 - Each requires some hand curation
 - Need to be readily accessible, and manipulable by interested researchers
 
---
# Potential alternatives
 - SQL database
 - Mongo, couchDB
 - git/github

---
# We chose git!

 - trees and annotations by study in Nexson format
 - Whole datastore is a git repo!  
 <img src="git.jpeg" />

---
# Organization

- Each study is a nexson file (can be easily translated to nexml, nexus, or newick using peyotl)
- Open Tree Taxonomy Index
- given the study ID what shard will it be in.
- scales better in general.

- Data is so open.

---
#Pros:
 - Familiarity
 No navigating someone else's complex schema

---
#Pros:
 - Tracking curation attribution
## Curation of phylogenies
 - Non-trivial effort 
 - Taxonomic name recognition services
 - Some subjective choices, edits made by many in the community over time
 
---
#Pros:
 - These trees are the backend for OpenTree Showpiece,  
## the synthetic tree!
 - but also a useful datastore for otehr phylogeneticists
 - Repo is hosted on GitHub, entire data store can be easily cloned and updated
 
---
# Pros
## Hosting on Github
 - Free
 - Familar
---
# Cons:
 - Phylogenies are hard to diff - rerooting changes everything!
 - simple data structures behave oddly...
 - repo size limits on github
 
# 

---
# Is a git datastore right for you?

 - How am I supposedd to know?!

---
# Thank you



