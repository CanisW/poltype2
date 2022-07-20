import sys
import os
from openbabel import openbabel
from rdkit import Chem
import numpy as np
from openbabel import pybel
import databaseparser


def gen_canonicallabels(poltype,mol,rdkitmol=None,usesym=True,isparent=False):
    """
    Intent: Using ring membership, and graph distance to all other elements compute symmetry type.
    Input: Openbabel MOL object.
    Output: Dictionary of atom index to symmetry type.
    Referenced By: GenerateParameters in poltype.py 
    Description: First find matching indices via symmetry type, then sort atom types so that groups of heavier atoms get lower type numbers. Optionally read in custom index to type number file if user provides input. 
    """
    if rdkitmol==None:
        obConversion = openbabel.OBConversion()
        obConversion.SetOutFormat('mol')
        obConversion.WriteFile(mol,'symm.mol')
        temptotalcharge=poltype.totalcharge
        rdkitmol=Chem.MolFromMolFile('symm.mol',removeHs=False,sanitize=False)
        poltype.totalcharge=None
        rdkitmol,atomindextoformalcharge=poltype.CheckInputCharge(rdkitmol)
        poltype.totalcharge=temptotalcharge
        Chem.SanitizeMol(rdkitmol)
    distmat=Chem.rdmolops.GetDistanceMatrix(rdkitmol)
    indextomatchingindices=ComputeSymmetryTypes(poltype,distmat,rdkitmol,mol,usesym)

    groups=[] 
    grouptoheavy={}
    for index,matchingindices in indextomatchingindices.items():
        atom=rdkitmol.GetAtomWithIdx(index)
        atomnum=atom.GetAtomicNum()
        heavy=False
        if atomnum!=1:
            heavy=True
        if set(matchingindices) not in groups:
            groups.append(set(matchingindices))
            grouptoheavy[tuple(set(matchingindices))]=heavy
        
    sortedgroups=[]
    for group,heavy in grouptoheavy.items():
        if heavy==True:
            if group not in sortedgroups:
                sortedgroups.append(group)
    for group,heavy in grouptoheavy.items():
        if heavy==False:
            if group not in sortedgroups:
                sortedgroups.append(group)
    symclasstogrp={}
    idxtosymclass={}
    symclass=poltype.prmstartidx
    for grp in sortedgroups:
        symclasstogrp[symclass]=grp
        symclass+=1
    for symclass,grp in symclasstogrp.items():
        for index in grp:
            idxtosymclass[index+1]=symclass
    if poltype.indextotypefile!=None and isparent==True:
        idxtosymclass=ReadCustomIndexToTypeFiles(poltype,poltype.indextotypefile)
    symmetryclass=idxtosymclass.values()
    return idxtosymclass,symmetryclass


def ComputeSymmetryTypes(poltype,distmat,rdkitmol,mol,usesym):
    """
    Intent: Define symmetry type by a graph invarient vector. If two atoms have the same GI vector than they have the same type.
    Input: Pairwise topological distance matrix, MOL object 
    Output: Dictionary of atom index to matching atom indices
    Referenced By: gen_canonicallabels
    Description: 
    1. Compute GI vector for every atom
    2. Iterate over GI vectors for each atom and check if their is GI vector match, if so add to same group
    3. If usesym==False then use atom index instead of type numbers.
    """
    indextomatchingindices={}
    indextoGI={}
    if usesym==True:
        atomindices=databaseparser.RingAtomicIndices(poltype,mol)
        for atom in rdkitmol.GetAtoms():
            atomidx=atom.GetIdx()
            GI=ComputeGIVector(poltype,atom,rdkitmol,distmat,mol,atomindices)
            indextoGI[atomidx]=GI

        for index,GI in indextoGI.items():
            for oindex,oGI in indextoGI.items():
                if GI==oGI:
                    if index not in indextomatchingindices.keys():
                        indextomatchingindices[index]=[]
                    if oindex not in indextomatchingindices[index]:
                        indextomatchingindices[index].append(oindex)
    else:
        for atom in rdkitmol.GetAtoms():
            atomidx=atom.GetIdx()
            indextomatchingindices[atomidx]=atomidx

    return indextomatchingindices


def ReadCustomIndexToTypeFiles(poltype,indextotypefile):
    """
    Intent: If user provides file mapping atom index to type, read that in as symmetry types.
    Input: indextotypefile
    Output:
    Referenced By: gen_canonicallabels
    Description: indextomatchingindices
    """
    indextomatchingindices={}
    temp=open(indextotypefile,'r')
    results=temp.readlines()
    temp.close()
    for line in results:
        linesplit=line.split()
        if len(linesplit)!=0:
            index=int(linesplit[0])
            typenumber=int(linesplit[1])
            indextomatchingindices[index]=typenumber
    return indextomatchingindices




def ComputeGIVector(poltype,atom,rdkitmol,distmat,mol,atomindices):
    """
    Intent:
    Input: Atom of interest object, rdkit MOL object, pairwise topological distance matrix, openbabel MOL object, list of list of ring atomic indices.
    Output: Graph Invariant Vector
    Referenced By: ComputeSymmetryTypes
    Description:
    1. Grab topological distances to every other atom in graph.  
    2. Determine unique topological distances from atom.
    3. For each unique topological distance from atom, find all other atoms at same distance away and save the atomic number of that atom.
    4. Then count how many atoms of same atomic number are at that distance away from original atom.
    5. Now for every distance d, away from atom of interest a, you have a map of atomic number to number of occurances of atomic number at that distance. This is in essence what the symmetry type number is.
    6.
    """
    GI=[]
    atomidx=atom.GetIdx()
    distances=distmat[atomidx]
    indices=np.array(list(range(len(distances))))
    indextodist=dict(zip(indices,distances))
    distancetoatomicnumcounts={}
    
    uniquedistances=set(distances)
    for d in uniquedistances:
        if d not in distancetoatomicnumcounts.keys():
            distancetoatomicnumcounts[d]={}
            atomicnums=[]
            for index,dist in indextodist.items():
                oatom=rdkitmol.GetAtomWithIdx(int(index))
                atomicnum=oatom.GetAtomicNum()
                if dist==d:
                    atomicnums.append(atomicnum)
            uniqueatomicnums=set(atomicnums)
            atomicnumtocount={}
            for atomnum in uniqueatomicnums:
                count=atomicnums.count(atomnum)
                atomicnumtocount[atomnum]=count
            distancetoatomicnumcounts[d]=atomicnumtocount
    sorteddistancetoatomicnumcounts=dict(sorted(distancetoatomicnumcounts.items()))
    for d,dic in sorteddistancetoatomicnumcounts.items():
        sortedatomicnumtocount=dict(sorted(dic.items()))
        ls=[]
        for atmnum,count in sortedatomicnumtocount.items():
            ls.append(atmnum*count)
        GI.extend(ls)



    neighbs=[natom for natom in atom.GetNeighbors()]
    numneighbs=len(neighbs)
    isaro=atom.GetIsAromatic()
    isinring=mol.GetAtom(atomidx+1).IsInRing()
    atomicnum=atom.GetAtomicNum()
    GI.append(atomicnum)
    atmnumtocount={}
    if numneighbs==1:
       neighb=neighbs[0]
       natomidx=neighb.GetIdx()
       rings=databaseparser.GrabAllRingsContainingIndices(poltype,atomindices,[natomidx+1])
    else:
       rings=databaseparser.GrabAllRingsContainingIndices(poltype,atomindices,[atomidx+1])
    if len(rings)>0:
        for ring in rings:
            if len(ring)<=7: # openbabel doesnt count all ring memership right someitmes when whole molecule is giant ring
                for atomindex in ring:
                    atom=rdkitmol.GetAtomWithIdx(atomindex-1)
                    atomicnum=atom.GetAtomicNum()
                    if atomicnum not in atmnumtocount.keys():
                        atmnumtocount[atomicnum]=0
                    atmnumtocount[atomicnum]+=1
        ls=[]
        sortedatmnumtocount=dict(sorted(atmnumtocount.items()))
        for atmnum,count in sortedatmnumtocount.items():
            ls.append(atmnum*count)
        GI.extend(ls)


    
    return GI
