import os, numpy as np
import sys
import csv
import getopt
import shutil
from openbabel import openbabel
from rdkit.Chem import rdmolfiles
from rdkit.Chem import Descriptors
import re
import numpy as np
from rdkit import Chem
import subprocess
import itertools 
import csv
import time


def GrabMoleculeOrder(poltypepathlist,nametopropsarray):
    nametoarrayindexorder={}
    for name in nametopropsarray.keys():
        if name=='':
            continue
        foundname=False
        for poltypepathidx in range(len(poltypepathlist)):
            poltypepath=poltypepathlist[poltypepathidx]
            if name in poltypepath:
                foundname=True
                break
        if foundname==False:
            continue
        nametoarrayindexorder[name]=poltypepathidx 
    return nametoarrayindexorder


def GrabArrayInputs(nametopropsarray,nametoarrayindexorder):
    arrayindexordertoname = {v: k for k, v in nametoarrayindexorder.items()}
    temperature_list=[]
    pressure_list=[]
    enthalpy_of_vaporization_list=[]
    density_list=[]
    tempstring='Temperature (K)'
    pressurestring='Pressure (atm)'
    densitystring='Density (Kg/m^3)'
    enthalpystring='Enthalpy (kJ/mol)'
    sortednametoarrayindexorder={k: v for k, v in sorted(arrayindexordertoname.items(), key=lambda item: item[0])}
    for arrayidx,name in sortednametoarrayindexorder.items():
        propsdict=nametopropsarray[name]
        temp=propsdict[tempstring]
        pressure=propsdict[pressurestring]
        density=propsdict[densitystring]
        enthalpy=propsdict[enthalpystring]
        temperature_list.append(temp)
        pressure_list.append(pressure)
        enthalpy_of_vaporization_list.append(enthalpy)
        density_list.append(density)   

    return temperature_list,pressure_list,enthalpy_of_vaporization_list,density_list


def FindIndexWithString(string,array):
    found=False
    for i in range(len(array)):
        e=array[i]
        if string in e:
            found=True
            break
    if found==False:
        raise ValueError(string+'  was not found in header')
    return i


def CheckNoneValue(value):
    try:
        float(value)
    except:
        value='UNK'
    return value 


def ReadCSVFile(csvfileread,poltypepathlist):
    with open(csvfileread, newline='') as csvfile:
        reader = list(csv.reader(csvfile, delimiter=',', quotechar='|'))
        header=reader[0]
        namestring='Name'
        tempstring='Temperature (K)'
        pressurestring='Pressure (atm)'
        densitystring='Density (Kg/m^3)'
        enthalpystring='Enthalpy (kJ/mol)'
        nameindex=FindIndexWithString(namestring,header)
        tempindex=FindIndexWithString(tempstring,header)
        pressureindex=FindIndexWithString(pressurestring,header)
        densityindex=FindIndexWithString(densitystring,header)
        enthalpyindex=FindIndexWithString(enthalpystring,header)
        nametopropsarray={} 
        for rowidx in range(1,len(reader)):
            row=reader[rowidx]
            name=row[nameindex]
            if name=='':
                continue
            temp=CheckNoneValue(row[tempindex])
            pressure=CheckNoneValue(row[pressureindex])
            density=CheckNoneValue(row[densityindex])
            enthalpy=CheckNoneValue(row[enthalpyindex])
            if name not in nametopropsarray.keys():
                nametopropsarray[name]={}
            if tempstring not in nametopropsarray[name].keys():
                nametopropsarray[name][tempstring]=[]
            nametopropsarray[name][tempstring].append(temp)
            if pressurestring not in nametopropsarray[name].keys():
                nametopropsarray[name][pressurestring]=[]
            nametopropsarray[name][pressurestring].append(pressure)
            if densitystring not in nametopropsarray[name].keys():
                nametopropsarray[name][densitystring]=[]
            nametopropsarray[name][densitystring].append(density)
            if enthalpystring not in nametopropsarray[name].keys():
                nametopropsarray[name][enthalpystring]=[]
            nametopropsarray[name][enthalpystring].append(enthalpy)
        for path in poltypepathlist:
            head,name=os.path.split(path)
            if name not in nametopropsarray.keys():
                nametopropsarray[name]={}
            if tempstring not in nametopropsarray[name].keys():
                nametopropsarray[name][tempstring]=[]
            if pressurestring not in nametopropsarray[name].keys():
                nametopropsarray[name][pressurestring]=[]
            if densitystring not in nametopropsarray[name].keys():
                nametopropsarray[name][densitystring]=[]
            if enthalpystring not in nametopropsarray[name].keys():
                nametopropsarray[name][enthalpystring]=[]


    return nametopropsarray



def ShapeOfArray(array):
    dimlist=[]
    rows=len(array)
    dimlist.append(rows)
    for i in range(len(array)):
        row=array[i]
        cols=len(row)
        dimlist.append(cols)
    return dimlist

def CheckInputShapes(listofarrays):
    combs=itertools.combinations(listofarrays, 2)
    for comb in combs:
        arr1=comb[0]
        arr2=comb[1]
        shape1=ShapeOfArray(arr1)
        shape2=ShapeOfArray(arr2)
        if shape1!=shape2:
            raise ValueError('Input dimensions for Temperature, Pressure or Density are not the same') 

def GenerateNoneList(targetshape):
    ls=[]
    rows=targetshape[0]
    cols=targetshape[1:]
    for i in range(rows):
        colnum=cols[i]
        newls=[]
        for j in range(colnum):
            newls.append(None)
        ls.append(newls)
    return ls 




def CombineData(temperature_list,pressure_list,enthalpy_of_vaporization_list,enthalpy_of_vaporization_err_list,surface_tension_list,surface_tension_err_list,relative_permittivity_list,relative_permittivity_err_list,isothermal_compressibility_list,isothermal_compressibility_err_list,isobaric_coefficient_of_volume_expansion_list,isobaric_coefficient_of_volume_expansion_err_list,heat_capacity_at_constant_pressure_list,heat_capacity_at_constant_pressure_err_list,density_list,density_err_list,citation_list):
    listoftptopropdics=[]
    for i in range(len(temperature_list)):
        temperatures=temperature_list[i]
        pressures=pressure_list[i]
        enthalpies=enthalpy_of_vaporization_list[i]
        enthalpies_err=enthalpy_of_vaporization_err_list[i]
        surf_tens=surface_tension_list[i]
        surf_tens_err=surface_tension_err_list[i]
        perms=relative_permittivity_list[i]
        perms_err=relative_permittivity_err_list[i]
        compress=isothermal_compressibility_list[i]
        compress_err=isothermal_compressibility_err_list[i]
        volumeexp=isobaric_coefficient_of_volume_expansion_list[i]
        volumeexp_err=isobaric_coefficient_of_volume_expansion_err_list[i]
        heatcap=heat_capacity_at_constant_pressure_list[i]
        heatcap_err=heat_capacity_at_constant_pressure_err_list[i]
        densities=density_list[i]
        densities_err=density_err_list[i]
        citations=citation_list[i]
        tptoproptovalue={}
        for j in range(len(temperatures)):
            temp=temperatures[j]
            pressure=pressures[j]
            tp=tuple([temp,pressure])
            tptoproptovalue[tp]={}   
            enthalpy=enthalpies[j]
            enthalpy_err=enthalpies_err[j]
            surf_ten=surf_tens[j] 
            surf_ten_err=surf_tens_err[j]
            perm=perms[j]
            perm_err=perms_err[j]
            comp=compress[j]
            comp_err=compress_err[j]
            volexp=volumeexp[j]
            volexp_err=volumeexp_err[j]
            cap=heatcap[j]
            cap_err=heatcap_err[j]
            density=densities[j]
            density_err=densities_err[j]
            citation=citations[j]
            tptoproptovalue[tp]['T']=temp
            tptoproptovalue[tp]['P']=pressure
            tptoproptovalue[tp]['Hvap']=enthalpy
            tptoproptovalue[tp]['Hvap_err']=enthalpy_err
            tptoproptovalue[tp]['Surf_Ten']=surf_ten
            tptoproptovalue[tp]['Surf_Ten_err']=surf_ten_err
            tptoproptovalue[tp]['Eps0']=perm
            tptoproptovalue[tp]['Eps0_err']=perm_err
            tptoproptovalue[tp]['Kappa']=comp
            tptoproptovalue[tp]['Kappa_err']=comp_err
            tptoproptovalue[tp]['Alpha']=volexp
            tptoproptovalue[tp]['Alpha_err']=volexp_err
            tptoproptovalue[tp]['Cp']=cap
            tptoproptovalue[tp]['Cp_err']=cap_err
            tptoproptovalue[tp]['Rho']=density
            tptoproptovalue[tp]['Rho_err']=density_err
            tptoproptovalue[tp]['cite']=citation

        listoftptopropdics.append(tptoproptovalue)
    return listoftptopropdics


       
def AddDefaultValues(tptoproptovalue):
    for tp,proptovalue in tptoproptovalue.items():
        globaldic={}
        defaultdenomvalue=1
        wtkeywordtovalue={}
        
        for prop,value in proptovalue.items():
            if prop!='name' and prop!='cite' and 'err' not in prop and prop!='T' and prop!='P':
                lowerprop=prop.lower()
                keyword=lowerprop+'_denom'
                globaldic[keyword]=defaultdenomvalue
                weightkeyword=prop+'_wt'
                try:
                    length=float(value)
                    defaultwtvalue=1
                except:
                    defaultwtvalue=0
                wtkeywordtovalue[weightkeyword]=defaultwtvalue

   
        proptovalue['global']=globaldic
        for wtkeyword,wtvalue in wtkeywordtovalue.items():
            proptovalue[wtkeyword]=wtvalue

        tptoproptovalue[tp]=proptovalue


    return tptoproptovalue


def WriteCSVFile(listoftpdics,nvtprops,molname):
    firsttpdic=listoftpdics[0]
    firsttpdicvalues=list(firsttpdic.values())
    firsttppointvalues=firsttpdicvalues[0]
    firstglobaldic=firsttppointvalues['global']
    nvtproperties=['Surf_Ten']
    with open('data'+'_'+molname+'.csv', mode='w') as write_file:
        writer = csv.writer(write_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for keyword,value in firstglobaldic.items():
            ls=['Global',keyword,value]
            writer.writerow(ls) 
        writer.writerow([])
        listofcommentrows=[]
        listoftprows=[]
        listoftpcommentrows=[]
        for tpdic in listoftpdics:
            for tp,proptovalue in tpdic.items():
                citation=proptovalue['cite']
                refls=['# Ref',citation]
                propls=['T','P']
                propvaluels=[str(tp[0]),str(tp[1])+' '+'atm']
                properrls=[]
                properrvaluels=[]
                commentpropvaluels=['# '+str(tp[0]),str(tp[1])+' '+'atm']

                ls=[refls,commentpropvaluels]
                for prop,value in proptovalue.items():
                    if prop!='cite' and 'wt' not in prop and 'err' not in prop and prop!='T' and prop!='P' and 'global' not in prop:
                        #if value==None:
                        #    continue
                        if value=='UNK':
                            value=None
                        if nvtprops==False and prop in nvtproperties:
                            continue

                        propls.append(prop)
                        propvaluels.append(value)
                        wtkeyword=prop+'_wt'
                        wtvalue=proptovalue[wtkeyword]
                        propls.append(wtkeyword)
                        propvaluels.append(wtvalue)
                        errkeyword=prop+'_err'
                        errvalue=proptovalue[errkeyword]
                        if errvalue==None:
                            errvalue=0
                        properrls.append(errkeyword)
                        properrvaluels.append(errvalue)
                properrls[0]='# '+str(properrls[0])
                properrvaluels[0]='# '+str(properrvaluels[0])

                ls.append(properrls) 
                ls.append(properrvaluels)
                listofcommentrows.append(ls)
                listoftpcommentrows.append(propls)
                listoftprows.append(propvaluels)
        for grpls in listofcommentrows:
            for ls in grpls:
                writer.writerow(ls)
            writer.writerow([])
        first=listoftpcommentrows[0]
        writer.writerow(first)
        for ls in listoftprows:
            writer.writerow(ls)
                        

def GenerateLiquidCSVFile(nvtprops,listoftptopropdics,molnamelist):
    indextogeneratecsv={}
    for i in range(len(molnamelist)):
        allunknown=True
        if len(listoftptopropdics)==len(molnamelist):
            tptoproptovalue=listoftptopropdics[i]
            molname=molnamelist[i]
            for tp,proptovalue in tptoproptovalue.items():
                t=tp[0]
                p=tp[1]
                if t!='UNK' and p!='UNK':
                    allunknown=False

            if allunknown==False:
                tptoproptovalue=AddDefaultValues(tptoproptovalue)
                WriteCSVFile([tptoproptovalue],nvtprops,molname)
        if allunknown==False:
            gencsv=True
        else:
            gencsv=False
        indextogeneratecsv[i]=gencsv
    return indextogeneratecsv

def ReadInPoltypeFiles(poltypepathlist):
    dimertinkerxyzfileslist=[]
    dimerenergieslist=[]
    dimersplogfileslist=[]
    keyfilelist=[]
    xyzfilelist=[]
    molnamelist=[]
    molfilelist=[]
    finalxyzfilelist=[]
    for poltypepath in poltypepathlist:
        dimertinkerxyzfiles=[]
        dimerenergies=[]
        dimersplogfiles=[]
        curdir=os.getcwd()
        os.chdir(poltypepath)
        keyfile=os.path.join(poltypepath,'final.key')
        finalxyzfile=os.path.join(poltypepath,'final.xyz')
        if not os.path.exists(keyfile) or not os.path.exists(finalxyzfile):
            raise ValueError('Final xyz or keyfile does not exist in '+str(poltypepath))
        logtoxyz={}
        if os.path.isdir('vdw'):
            os.chdir('vdw')
            files=os.listdir()
            spext='_sp.log'
            for f in files:
                if spext in f:
                    tempxyzfile=f.replace(spext,'.xyz')
                    xyzfile=os.path.join(os.getcwd(),tempxyzfile)
                    logfile=os.path.join(os.getcwd(),f)
                    if os.path.isfile(xyzfile):
                        dimertinkerxyzfiles.append(xyzfile)
                        dimersplogfiles.append(logfile)
                        logtoxyz[logfile]=xyzfile
            os.chdir('..')
        else:
            raise ValueError('vdw folder does not exist for '+poltypepath)

        files=os.listdir()
        for f in files:
            if '.' in f:
                filesplit=f.split('.')
                ext=filesplit[1]
                if ext=='sdf': # assume poltype input sdf file
                    molname=filesplit[0]
                    molfile=f


        dimerenergies,dimersplogfiles=ReadQMLogFile(dimersplogfiles)
        molfile=os.path.join(poltypepath,molfile)
        os.chdir(curdir)
        newdimertinkerxyzfiles=[]
        for log,xyz in logtoxyz.items():
            if log in dimersplogfiles:
                newdimertinkerxyzfiles.append(xyz)
                   
        dimertinkerxyzfileslist.append(newdimertinkerxyzfiles)
        dimerenergieslist.append(dimerenergies)
        dimersplogfileslist.append(dimersplogfiles)
        keyfilelist.append(keyfile)
        finalxyzfilelist.append(finalxyzfile)
        xyzfilelist.append(xyzfile)
        molnamelist.append(molname)
        molfilelist.append(molfile)

    return keyfilelist,xyzfilelist,dimertinkerxyzfileslist,dimerenergieslist,molnamelist,molfilelist,dimersplogfileslist,finalxyzfilelist
 

def GrabMonomerEnergy(line,Hartree2kcal_mol):
    linesplit=line.split()
    energy=float(linesplit[4]) 
    monomerenergy=(energy)
    return monomerenergy

def CheckIfLogFileUsingGaussian(f):
    use_gaus=False
    temp=open(f,'r')
    results=temp.readlines()
    temp.close()
    for line in results:
        if 'Entering Gaussian System' in line:
            use_gaus=True
            break 
    return use_gaus

 
def ReadQMLogFile(dimersplogfiles):
    Hartree2kcal_mol=627.5095
    dimerenergies=[]
    newdimersplogfiles=[]
    for f in dimersplogfiles:
        interenergy=None
        use_gaus=CheckIfLogFileUsingGaussian(f)
        tmpfh=open(f,'r')
        if use_gaus==True:
            frag1calc=False
            frag2calc=False
            found=False
            for line in tmpfh:
                if 'Counterpoise: corrected energy =' in line:
                    dimerenergy=float(line.split()[4])
                    found=True
                elif 'Counterpoise: doing DCBS calculation for fragment   1' in line:
                    frag1calc=True
                    frag2calc=False
                elif 'Counterpoise: doing DCBS calculation for fragment   2' in line:
                    frag1calc=False
                    frag2calc=True
                elif 'SCF Done' in line:
                    if frag1calc:
                        frag1energy=GrabMonomerEnergy(line,Hartree2kcal_mol)
                    elif frag2calc:
                        frag2energy=GrabMonomerEnergy(line,Hartree2kcal_mol)
            if found==True:
                interenergy=dimerenergy-(frag1energy+frag2energy)
        else:
            for line in tmpfh:
                if 'CP Energy =' in line and 'print' not in line:
                    linesplit=line.split()
                    interenergy=float(linesplit[3])
        if interenergy!=None:
            dimerenergies.append(interenergy)    
            newdimersplogfiles.append(f)
        tmpfh.close()
    

    return dimerenergies,newdimersplogfiles


def GrabVdwTypeLinesFromFinalKey(keyfilelist,vdwtypeslist):
    vdwtypelineslist=[]
    for i in range(len(keyfilelist)):
        vdwtypelines=[]
        keyfile=keyfilelist[i]
        vdwtypes=vdwtypeslist[i]
        temp=open(keyfile,'r')
        results=temp.readlines()
        temp.close()
        for line in results:
            if 'vdw' in line:
                for vdwtype in vdwtypes:
                    if str(vdwtype) in line:
                        vdwtypelines.append(line)
        vdwtypelineslist.append(vdwtypelines)

    return vdwtypelineslist

def GenerateForceFieldFiles(vdwtypelineslist,moleculeprmfilename,fittypestogether,keyfilelines,addwaterprms,prmfilelines,vdwprmtypestofit,vdwtypestoeval,vdwtypeslist):
    vdwtypetoindex={'S':2,'T':3,'D':4}
    prmtypestofit=[vdwtypetoindex[i] for i in vdwprmtypestofit]
    prmtypestoeval=[vdwtypetoindex[i] for i in vdwtypestoeval]
    transferprmstofit=[]
    for index in vdwtypetoindex.values():
        if index not in prmtypestoeval:
            if index==4:
                 if 4 in prmtypestofit:
                     transferprmstofit.append(index)

            else:
                transferprmstofit.append(index)
    try:
        length=len(fittypestogether)
        indextogroup={}
        array=[]
        for i in range(len(fittypestogether)):
            row=fittypestogether[i]
            for j in range(len(row)):
                if j not in indextogroup.keys():
                    indextogroup[j]=[]
                value=row[j]
                indextogroup[j].append(value)
        for index,group in indextogroup.items():
            array.append(group)
                 
                
    except:
        array=[]
    if not os.path.isdir('forcefield'):
        os.mkdir('forcefield')
    os.chdir('forcefield')
    vdwtypetoline={}
    vdwtypetored={}
    typestonothaveprmkeyword=[]
    if len(array)!=0:
        for row in array:
            firsttype=row[0] # this one we reference and dont append
            rest=row[1:]
            for vdwtype in rest:
                typestonothaveprmkeyword.append(int(vdwtype))
    for vdwtypelines in vdwtypelineslist:
        for line in vdwtypelines:
            linesplit=line.split()
            vdwtype=int(linesplit[1])
            last=float(linesplit[-1])
            linelen=len(linesplit)
            linesplit.append('#')
            if vdwtype not in typestonothaveprmkeyword:
                linesplit.append('PRM')
                if 2 in prmtypestofit:
                    linesplit.append('2')
                if 3 in prmtypestofit:
                    linesplit.append('3')
                if 4 in prmtypestofit:
                    if linelen==5 and last!=1:
                        if 4 in prmtypestofit:
                            linesplit.append('4')
                        else:
                            linesplit[4]='1 # '
                else:
                    if linelen==5 and last!=1:
                        linesplit[4]='1 # '
            
            if linelen==5 and last!=1:
                vdwtypetored[vdwtype]=True
            else:
                vdwtypetored[vdwtype]=False
            if 4 not in prmtypestofit:
                if linelen==5 and last!=1:
                    linesplit[4]='1 # '
                vdwtypetored[vdwtype]=False
            newline=' '.join(linesplit)+'\n'
            vdwtypetoline[vdwtype]=newline   
    if len(array)!=0:
        for row in array:
            firsttype=row[0] # this one we reference and dont append
            rest=row[1:]
            for vdwtype in rest:
                line=vdwtypetoline[int(vdwtype)]
                red=vdwtypetored[int(vdwtype)]
                line=line.replace('\n','')
                if len(transferprmstofit)!=0:
                    line+=" PRM"
                    for idx in transferprmstofit:
                        line+=' '+str(idx) 
   
                line+=" EVAL "
                if 2 in prmtypestoeval:
                    line+="2 PRM['VDWS/%s']"%(str(firsttype)) 
                if 3 in prmtypestoeval:
                    line+=" 3 PRM['VDWT/%s']"%(str(firsttype)) 
                if red==True:
                    if 4 in prmtypestoeval:
                        line+=" 4 PRM['VDWD/%s']"%(str(firsttype)) 

                line+='\n'
                vdwtypetoline[int(vdwtype)]=line

    molprmfilepath=os.path.join(os.getcwd(),moleculeprmfilename)
    temp=open(moleculeprmfilename,'w')
    for vdwtype,line in vdwtypetoline.items():
        temp.write(line)
    temp.write('\n')
    for keyfilels in keyfilelines:
        for line in keyfilels:
            temp.write(line)
    if addwaterprms==True:
        waterlines=WaterParameters()
        for line in waterlines:
            temp.write(line+'\n')
    temp.write('\n')
    for line in prmfilelines:
        temp.write(line)

    temp.close()
    temp.close()
    for vdwtypes in vdwtypeslist:
        CommentOutVdwLines(molprmfilepath,vdwtypes)
        time.sleep(1)
    time.sleep(2)
    os.chdir('..')
    shutil.copy(molprmfilepath,os.path.join(os.getcwd(),moleculeprmfilename))
    return molprmfilepath
    
def RemoveKeyWord(keypath,keystring):
    read=open(keypath,'r')
    results=read.readlines()
    read.close()
    tempname=keypath.replace('.key','-t.key')
    temp=open(tempname,'w')
    for line in results:
        if keystring not in line:
            temp.write(line)
    temp.close()
    os.remove(keypath)
    os.rename(tempname,keypath)  


def CommentOutVdwLines(keypath,vdwtypes):
    read=open(keypath,'r')
    results=read.readlines()
    read.close()
    if '.key' in keypath:
        tempname=keypath.replace('.key','-t.key')
    else:
        tempname=keypath.replace('.prm','-t.prm')

    temp=open(tempname,'w')
    for lineidx in range(len(results)):
        line=results[lineidx]
        for vdwtype in vdwtypes:
            if (' '+str(vdwtype)+' ') in line and 'vdw' in line and 'PRM' not in line and 'EVAL' not in line:
                newline='# '+line
                results[lineidx]=newline
    for line in results:
        temp.write(line) 
    


    temp.close()
    os.remove(keypath)
    os.rename(tempname,keypath)  


def GenerateLiquidTargetsFolder(gaskeyfilelist,gasxyzfilelist,liquidkeyfilelist,liquidxyzfilelist,datacsvpathlist,densitylist,originalliquidfolder,prmfilepath,moleculeprmfilename,vdwtypeslist,addwaterprms,molnamelist,indextogeneratecsv):
    liquidfolderlist=[]
    for i in range(len(gaskeyfilelist)):
        gencsv=indextogeneratecsv[i]
        gaskeyfile=gaskeyfilelist[i]
        gasxyzfile=gasxyzfilelist[i]
        liquidkeyfile=liquidkeyfilelist[i]
        liquidxyzfile=liquidxyzfilelist[i]
        datacsvpath=datacsvpathlist[i]
        vdwtypes=vdwtypeslist[i]
        molname=molnamelist[i]
        if not os.path.isdir('targets'):
            os.mkdir('targets')
        os.chdir('targets')
        liquidfolder=originalliquidfolder+'_'+molname
        liquidfolderlist.append(liquidfolder) 
        if gencsv==False:
            os.chdir('..')
            continue
        if not os.path.isdir(liquidfolder):
            os.mkdir(liquidfolder)
        os.chdir(liquidfolder)
        shutil.copy(gaskeyfile,os.path.join(os.getcwd(),'gas.key'))
        RemoveKeyWord(os.path.join(os.getcwd(),'gas.key'),'parameters')
        temp=open(os.path.join(os.getcwd(),'gas.key'),'a')
        
        temp.close() 
        string='parameters '+moleculeprmfilename+'\n'
        AddKeyWord(os.path.join(os.getcwd(),'gas.key'),string)
        string='digits 8'+'\n'
        AddKeyWord(os.path.join(os.getcwd(),'gas.key'),string)


        CommentOutVdwLines(os.path.join(os.getcwd(),'gas.key'),vdwtypes)
        shutil.copy(gasxyzfile,os.path.join(os.getcwd(),'gas.xyz'))
        if liquidkeyfile!=None: 
            shutil.copy(liquidkeyfile,os.path.join(os.getcwd(),'liquid.key'))
            CommentOutVdwLines(os.path.join(os.getcwd(),'liquid.key'),vdwtypes)
        if liquidxyzfile!=None:
            shutil.copy(liquidxyzfile,os.path.join(os.getcwd(),'liquid.xyz'))
            os.remove(liquidxyzfile)
        if datacsvpath!=None:
            shutil.copy(datacsvpath,os.path.join(os.getcwd(),'data.csv'))
            os.remove(datacsvpath)
        os.chdir('..')
        os.chdir('..')

    return liquidfolderlist

def FindDimensionsOfMoleculeTinker(structurefilepath):
    veclist=[]
    temp=open(structurefilepath,'r')
    results=temp.readlines()
    temp.close()
    for line in results:
        linesplit=line.split()
        if len(linesplit)!=1 and '90.000000' not in line: # not line containing number of atoms
            vec=np.array([float(linesplit[2]),float(linesplit[3]),float(linesplit[4])])
            veclist.append(vec)

    pairs=list(itertools.combinations(veclist, 2))
    distlist=[]
    for pairidx in range(len(pairs)):
        pair=pairs[pairidx]
        progress=(pairidx*100)/len(pairs)
        dist=np.linalg.norm(np.array(pair[0])-np.array(pair[1]))
        distlist.append(dist)
    mindist=np.amax(np.array(distlist))
    return mindist

def ComputeBoxLength(xyzfile,addextra=False):
    vdwcutoff=12 #in angstrom
    longestdim=FindDimensionsOfMoleculeTinker(xyzfile)
    aaxis = 2*float(vdwcutoff)+longestdim+4
    finalaxis=aaxis
    if addextra==True:
        finalaxis=aaxis+.1*aaxis # add 50%, since some molecules very repulsive such as benzene and need to run NPT dynamics to get correct box size and adequate starting structure for MD
    return aaxis,finalaxis


def CreateSolventBox(axis,molnumber,prmfilepath,xyzeditpath,tinkerxyzname,molname,keyfilels,molprmfilepath,liquidkeyfile):
    head,tail=os.path.split(tinkerxyzname)
    key=tail.replace('.xyz','.key')
    temp=open(key,'w')
    for line in keyfilels:
        temp.write(line)
    temp.flush()
    os.fsync(temp.fileno())
    temp.close()
    time.sleep(1)
    print('Creating Solvent Box For '+tinkerxyzname,flush=True)
    temp=open('xyzedit.in','w')
    temp.write('23'+'\n')
    temp.write(str(molnumber)+'\n')
    temp.write(str(axis)+','+str(axis)+','+str(axis)+'\n')
    temp.write('Y'+'\n')
    temp.close()
    cmdstr=xyzeditpath+' '+tail+' '+'-k'+' '+liquidkeyfile+' <'+' '+'xyzedit.in'
    call_subsystem(cmdstr,wait=True)
    os.replace(tail+'_2',molname+'_liquid.xyz') 
    liquidxyzfile=os.path.join(os.getcwd(),molname+'_liquid.xyz')
    return liquidxyzfile

def call_subsystem(cmdstr,wait=False):
    print('Calling: '+cmdstr,flush=True)
    p = subprocess.Popen(cmdstr, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if wait==True:
        p.wait()
        if p.returncode != 0:
            raise ValueError("ERROR: " + cmdstr+' '+'path'+' = '+os.getcwd())


def InsertKeyfileHeader(keyfilename,moleculeprmfilename,axis):
    ewaldcutoff=7
    integrator="RESPA"
    thermostat="BUSSI"
    vdwcutoff=12
    polareps=.00001
    barostatmethod='montecarlo'
    string='parameters '+moleculeprmfilename+'\n'
    AddKeyWord(keyfilename,string)
    string='a-axis'+' '+str(axis)+'\n'
    AddKeyWord(keyfilename,string)
    string='archive'+'\n'
    AddKeyWord(keyfilename,string)
    string='neighbor-list'+'\n'
    AddKeyWord(keyfilename,string)
    string='integrator '+integrator+'\n'
    AddKeyWord(keyfilename,string)
    string='thermostat '+thermostat+'\n'
    AddKeyWord(keyfilename,string)
    string='ewald'+'\n'
    AddKeyWord(keyfilename,string)
    string='vdw-cutoff '+str(vdwcutoff)+'\n'
    AddKeyWord(keyfilename,string)
    string='ewald-cutoff '+str(ewaldcutoff)+'\n'
    AddKeyWord(keyfilename,string)
    string='polar-eps '+str(polareps)+'\n'
    AddKeyWord(keyfilename,string)
    string='polar-predict'+'\n'
    AddKeyWord(keyfilename,string)
    string='barostat'+' '+barostatmethod+'\n'
    AddKeyWord(keyfilename,string)
    string='vdw-correction'+'\n'
    AddKeyWord(keyfilename,string)
    string='digits 8'+'\n'
    AddKeyWord(keyfilename,string)


def AddKeyWord(keypath,string):
    read=open(keypath,'r')
    results=read.readlines()
    read.close()
    if '.key' in keypath:
        tempkeyname=keypath.replace('.key','-t.key')
    else:
        tempkeyname=keypath.replace('.prm','-t.prm')

    temp=open(tempkeyname,'w')
    temp.write(string)
    for line in results:
        temp.write(line)
    temp.close()
    os.remove(keypath)
    os.rename(tempkeyname,keypath)


def WaterParameters():
    lines=[]
    lines.append('atom          349    90    O     "AMOEBAWaterO"               8    15.995    2')
    lines.append('atom          350    91    H     "AMOEBAWaterH"               1     1.008    1')
    lines.append('vdw         90   3.40058   0.06508')
    lines.append('vdw         91   2.64479   0.02601   0.91233')
    lines.append('bond          90    91          566.82  0.9571')
    lines.append('angle         91    90    91     48.98   106.58')
    lines.append('ureybrad      91    90    91      -12.50     1.5346')
    lines.append('multipole   349 -350 -350              -0.38282')
    lines.append('                                 0.00000    0.00000    0.29047')
    lines.append('                                 0.50815')
    lines.append('                                 0.00000   -0.68079')
    lines.append('                                 0.00000    0.00000    0.17264')
    lines.append('multipole   350  349  350               0.19141')
    lines.append('                                -0.07281    0.00000   -0.10315')
    lines.append('                                -0.01564')
    lines.append('                                 0.00000   -0.10967')
    lines.append('                                -0.04073    0.00000    0.12531')
    lines.append('polarize      349           0.9725      0.390    350')
    lines.append('polarize      350           0.4309      0.390    349 ')

    return lines

def GenerateNewKeyFile(keyfile,prmfilepath,moleculeprmfilename,axis,addwaterprms,molname):
    liquidkeyfile=shutil.copy(keyfile,os.path.join(os.getcwd(),molname+'_liquid.key'))
    RemoveKeyWord(liquidkeyfile,'parameters')
    temp=open(prmfilepath,'r')
    results=temp.readlines()
    temp.close()
    temp=open(liquidkeyfile,'a')
     
    
    InsertKeyfileHeader(liquidkeyfile,moleculeprmfilename,axis)

    return liquidkeyfile


def Minimize(liquidxyzfile,keyfile,minimizepath,prmfilepath):
    head,tail=os.path.split(prmfilepath)
    newprmfilepath=os.path.join(os.getcwd(),tail)
    shutil.copy(prmfilepath,newprmfilepath)
    outputfile=liquidxyzfile.replace('.xyz','min.out')
    minimizecmd=minimizepath+' '+liquidxyzfile+' '+'-k'+' '+keyfile+' '+'1'+ ' > '+outputfile
    call_subsystem(minimizecmd,wait=True)
    minxyz=liquidxyzfile.replace('.xyz','.xyz_2')
    os.remove(liquidxyzfile)
    os.replace(minxyz,liquidxyzfile)


def Analyze(liquidxyzfile,keyfile,analyzepath,prmfilepath):
    head,tail=os.path.split(prmfilepath)
    newprmfilepath=os.path.join(os.getcwd(),tail)
    shutil.copy(prmfilepath,newprmfilepath)
    outputfile=liquidxyzfile.replace('.xyz','alz.out')
    analyzecmd=analyzepath+' '+liquidxyzfile+' '+'-k'+' '+keyfile+' '+'e'+ ' > '+outputfile
    call_subsystem(analyzecmd,wait=True)
    CheckBondEnergy(outputfile)


def CheckBondEnergy(outputfile):
    temp=open(outputfile,'r')
    results=temp.readlines()
    temp.close()
    tol=.5
    for line in results:
        if 'Bond Stretching' in line:
            linesplit=line.split()
            intnum=int(linesplit[-1])
            energy=float(linesplit[-2])
            energyperbond=energy/intnum
            if energyperbond>tol:
                raise ValueError('Bad starting box structure, bond energy per bond is way to high '+str(energyperbond)+' kcal/mol')


def RemoveBoxLine(xyzfile):
    tempname=xyzfile.replace('.xyz','_TEMP.xyz')
    temp=open(xyzfile,'r')
    results=temp.readlines()
    temp.close()
    temp=open(tempname,'w')
    for line in results:
        if '90.00' not in line:
            temp.write(line)
    temp.close()
    os.remove(xyzfile)
    os.replace(tempname,xyzfile)


def AddKeyWord(keypath,string):
    read=open(keypath,'r')
    results=read.readlines()
    read.close()
    tempkeyname=keypath.replace('.key','-t.key')
    temp=open(tempkeyname,'w')
    temp.write(string)
    for line in results:
        temp.write(line)
    temp.close()
    os.remove(keypath)
    os.rename(tempkeyname,keypath)

def RemoveKeyWord(keypath,keystring):
    read=open(keypath,'r')
    results=read.readlines()
    read.close()
    tempname=keypath.replace('.key','-t.key')
    temp=open(tempname,'w')
    for line in results:
        if keystring not in line:
            temp.write(line)
    temp.close()
    os.remove(keypath)
    os.rename(tempname,keypath)


def DynamicCommand(dynamicpath,steps,ensemble,temp,outputfilename,boxfilename,configkeyfilename,timestep,writefreq,pressure=None):
    if pressure==None:
        cmdstr=dynamicpath+' '+boxfilename+' '+ '-k'+' '+configkeyfilename+' '+str(steps)+' '+ str(timestep)+' '+ str(writefreq)+' '+str(ensemble)+' '+str(temp)+' '+ ' > '+outputfilename  
    else:
        cmdstr=dynamicpath+' '+boxfilename+' '+ '-k'+' '+configkeyfilename+' '+str(steps)+' '+ str(timestep)+' '+ str(writefreq)+' '+str(ensemble)+' '+str(temp)+' '+str(pressure)+' '+ ' > '+outputfilename  
    call_subsystem(cmdstr,wait=True)




def GenerateTargetFiles(keyfilelist,xyzfilelist,densitylist,rdkitmollist,prmfilepath,xyzeditpath,moleculeprmfilename,addwaterprms,molnamelist,indextogeneratecsv,keyfilelines,minimizepath,molprmfilepath,finalxyzfilelist,analyzepath,dynamicpath,relaxFBbox):
    gaskeyfilelist=[]
    gasxyzfilelist=[]
    liquidkeyfilelist=[]
    liquidxyzfilelist=[] 
    datacsvpathlist=[]
    for i in range(len(rdkitmollist)):
        gencsv=indextogeneratecsv[i]
        rdkitmol=rdkitmollist[i]
        xyzfile=xyzfilelist[i]
        keyfile=keyfilelist[i]
        molname=molnamelist[i]
        keyfilels=keyfilelines[i]
        finalxyzfile=finalxyzfilelist[i]
        gaskeyfile=keyfile
        gasxyzfile=finalxyzfile
        if gencsv==True:
            density=float(densitylist[i])
            mass=Descriptors.ExactMolWt(rdkitmol)*1.66054*10**(-27) # convert daltons to Kg

            axis,finalaxis=ComputeBoxLength(gasxyzfile)
            boxlength=axis*10**-10 # convert angstroms to m
            numbermolecules=int(density*boxlength**3/mass)
            liquidkeyfile=GenerateNewKeyFile(keyfile,prmfilepath,moleculeprmfilename,finalaxis,addwaterprms,molname)

            liquidxyzfile=CreateSolventBox(finalaxis,numbermolecules,prmfilepath,xyzeditpath,gasxyzfile,molname,keyfilels,molprmfilepath,liquidkeyfile)
            AddKeyWord(liquidkeyfile,'polarizeterm none'+'\n')
            AddKeyWord(liquidkeyfile,'multipoleterm none'+'\n')
            Minimize(liquidxyzfile,liquidkeyfile,minimizepath,molprmfilepath)
            RemoveKeyWord(liquidkeyfile,'multipoleterm')
            Minimize(liquidxyzfile,liquidkeyfile,minimizepath,molprmfilepath)
            RemoveKeyWord(liquidkeyfile,'polarizeterm')
            Minimize(liquidxyzfile,liquidkeyfile,minimizepath,molprmfilepath)
            try:
                Analyze(liquidxyzfile,liquidkeyfile,analyzepath,molprmfilepath)
            except:
                print('Bond energy check failed, need to relax box more')
                sys.exit()
            if relaxFBbox==True:
                axis,finalaxis=ComputeBoxLength(gasxyzfile,addextra=True)
                boxlength=axis*10**-10 # convert angstroms to m
                numbermolecules=int(density*boxlength**3/mass)
                liquidkeyfile=GenerateNewKeyFile(keyfile,prmfilepath,moleculeprmfilename,finalaxis,addwaterprms,molname)

                liquidxyzfile=CreateSolventBox(finalaxis,numbermolecules,prmfilepath,xyzeditpath,gasxyzfile,molname,keyfilels,molprmfilepath,liquidkeyfile)
                AddKeyWord(liquidkeyfile,'polarizeterm none'+'\n')
                AddKeyWord(liquidkeyfile,'multipoleterm none'+'\n')
                Minimize(liquidxyzfile,liquidkeyfile,minimizepath,molprmfilepath)
                RemoveKeyWord(liquidkeyfile,'multipoleterm')
                Minimize(liquidxyzfile,liquidkeyfile,minimizepath,molprmfilepath)
                RemoveKeyWord(liquidkeyfile,'polarizeterm')
                Minimize(liquidxyzfile,liquidkeyfile,minimizepath,molprmfilepath)
                # now need to run dynamics to get correct box size
                AddKeyWord(liquidkeyfile,'polarizeterm none'+'\n')
                RemoveKeyWord(liquidkeyfile,'barostat')
                barostatmethod='berendsen'
                string='barostat'+' '+barostatmethod+'\n'
                AddKeyWord(liquidkeyfile,string)
                steps=250000
                ensemble=4
                temp=300
                outputfilename='boxrelax.out'
                timestep=2
                writefreq=10 
                pressure=1
                DynamicCommand(dynamicpath,steps,ensemble,temp,outputfilename,liquidxyzfile,liquidkeyfile,timestep,writefreq,pressure)

                
                RemoveKeyWord(liquidkeyfile,'polarizeterm')
                RemoveKeyWord(liquidkeyfile,'barostat')
                barostatmethod='montecarlo'
                string='barostat'+' '+barostatmethod+'\n'
                AddKeyWord(liquidkeyfile,string)
                steps=100000
                outputfilename='finalboxrelax.out'
                pressure=1
                DynamicCommand(dynamicpath,steps,ensemble,temp,outputfilename,liquidxyzfile,liquidkeyfile,timestep,writefreq,pressure)
                arcfilename=liquidxyzfile.replace('.xyz','.arc')
                framenum=int(os.path.getsize(arcfilename)/os.path.getsize(liquidxyzfile))
                ExtractTinkerFrames(arcfilename,framenum,framenum,1,framenum,liquidxyzfile)
            Analyze(liquidxyzfile,liquidkeyfile,analyzepath,molprmfilepath)
        else:
            liquidxyzfile=None
            liquidkeyfile=None
        
        
        name='data'+'_'+molname+'.csv'
        if os.path.exists(name):
            datacsvpath=os.path.join(os.getcwd(),name)
        else:
            datacsvpath=None
        gaskeyfilelist.append(gaskeyfile)
        gasxyzfilelist.append(gasxyzfile)
        liquidkeyfilelist.append(liquidkeyfile)
        liquidxyzfilelist.append(liquidxyzfile)
        datacsvpathlist.append(datacsvpath)
   

    return gaskeyfilelist,gasxyzfilelist,liquidkeyfilelist,liquidxyzfilelist,datacsvpathlist


def ExtractTinkerFrames(arcpath,firstframe,lastframe,framestep,totalnumberframes,newname):
    firstline=True
    framecount=0
    framestoextract=np.arange(firstframe,lastframe+1,framestep)
    framearray=[]
    extractingframe=False
    with open(arcpath) as infile:
        for line in infile:
            if firstline==True:
                firstlinesplit=line.split()
                framestring=firstlinesplit[0].lstrip().rstrip()
                firstline=False
           
            linesplit=line.split()
            if framestring in line and (len(linesplit)==1):
                extractingframe=False
                framecount+=1
                if len(framearray)!=0:
                    numberofzeroes=len(str(totalnumberframes))-len(str(framecount))
                    zerostring=''
                    for i in range(numberofzeroes):
                        zerostring+='0'
                    framename=arcpath.replace('.arc','.'+zerostring+str(framecount))
                    temp=open(framename,'w')
                    for saveline in framearray:
                        temp.write(saveline)
                    temp.close()
                    framearray=[]
                if framecount in framestoextract:
                    extractingframe=True
            if(extractingframe):
                framearray.append(line)
            if len(framearray)!=0: # for last frame
                numberofzeroes=len(str(totalnumberframes))-len(str(framecount))
                zerostring=''
                for i in range(numberofzeroes):
                    zerostring+='0'
                framename=arcpath.replace('.arc','.'+zerostring+str(framecount))
                temp=open(framename,'w')
                for saveline in framearray:
                    temp.write(saveline)
                temp.close()
    if os.path.exists(framename):
        os.rename(framename,newname)
    return

def GenerateQMTargetsFolder(dimertinkerxyzfileslist,dimerenergieslist,liquidkeyfilelist,originalqmfolder,vdwtypeslist,molnamelist):
    qmfolderlist=[]
    qmfolderlisttogen={}
    for j in range(len(dimertinkerxyzfileslist)):
        moldimertinkerxyzfiles=dimertinkerxyzfileslist[j]
        moldimerenergies=dimerenergieslist[j]
        liquidkeyfile=liquidkeyfilelist[j]
        molname=molnamelist[j]
        vdwtypes=vdwtypeslist[j]
        for k in range(len(moldimertinkerxyzfiles)):
            dimertinkerxyzfiles=moldimertinkerxyzfiles[k]
            dimerenergies=moldimerenergies[k]
            usefold=True
            if len(dimertinkerxyzfiles)==0:
                usefold=False
            if k==0:
                indexname='_water'
            elif k==1:
                indexname='_homodimer'
            qmfolder=originalqmfolder+'_'+molname+indexname
            qmfolderlist.append(qmfolder)
            qmfolderlisttogen[qmfolder]=usefold
            if usefold==True:
                if not os.path.exists('targets'):
                    os.mkdir('targets')
                os.chdir('targets')
                if not os.path.isdir(qmfolder):
                    os.mkdir(qmfolder)
                os.chdir(qmfolder)
                newnamearray=[]
                newenergyarray=[]
                arr=np.arange(0,len(dimertinkerxyzfiles))
                arcwriter=open('all.arc','w')
         
                for i in range(len(arr)):
                    value=arr[i]
                    tinkerxyzfile=dimertinkerxyzfiles[i]
                    dimerenergy=dimerenergies[i]
                    head,tail=os.path.split(tinkerxyzfile)
                    tinkerxyzfileprefix=tail.split('.')[0]
                    newname=tail+' '+str(value)
                    temp=open(tinkerxyzfile,'r')
                    results=temp.readlines()
                    temp.close() 
                    firstline=results[0]
                    firstlinesplit=firstline.split()
                    firstlinesplit.append(newname)
                    newfirstline=' '.join(firstlinesplit)+'\n'
                    results[0]=newfirstline
                    newnamearray.append(newname)
                    newenergyarray.append(dimerenergy) 
                    for line in results:
                        arcwriter.write(line)
                arcwriter.close()
                energywriter=open('qdata.txt','w')
                for i in range(len(arr)):
                    value=arr[i]
                    energy=newenergyarray[i]
                    firstline='LABEL'+' '+str(value)+'\n'
                    secondline='INTERACTION'+' '+str(energy)+'\n'
                    energywriter.write(firstline)
                    energywriter.write(secondline)
                    energywriter.write('\n')
                energywriter.close()
                if liquidkeyfile!=None:
                    shutil.copy(liquidkeyfile,os.path.join(os.getcwd(),'liquid.key'))
                    CommentOutVdwLines(os.path.join(os.getcwd(),'liquid.key'),vdwtypes)
                    if k==1:
                        os.remove(liquidkeyfile)
                os.chdir('..')
                os.chdir('..')
 
    return qmfolderlist,qmfolderlisttogen

def ReadLigandOBMol(structfname):
    tmpconv = openbabel.OBConversion()
    inFormat = openbabel.OBConversion.FormatFromExt(structfname)
    tmpconv.SetInFormat(inFormat)
    tmpmol = openbabel.OBMol()
    tmpconv.ReadFile(tmpmol, structfname)
    return tmpmol


def GenerateRdkitMol(ligandfilename):
    tmpmol=ReadLigandOBMol(ligandfilename)
    tmpconv = openbabel.OBConversion()
    tmpconv.SetOutFormat('mol')
    temp=ligandfilename.replace('.sdf','.mol')
    tmpconv.WriteFile(tmpmol, temp)
    rdkitmol=rdmolfiles.MolFromMolFile(temp,removeHs=False)
    return rdkitmol


def GenerateRdkitMolList(ligandfilenamelist):
    rdkitmollist=[]
    for ligandfilename in ligandfilenamelist:
        rdkitmol=GenerateRdkitMol(ligandfilename)
        rdkitmollist.append(rdkitmol)
    return rdkitmollist


def SanitizeMMExecutable(executable,tinkerdir):
    # Try to find Tinker executable with/without suffix
    if which(executable)!=None:
        return executable
    if tinkerdir is None:
        tinkerdir = os.getenv("TINKERDIR", default="")
    exe = os.path.join(tinkerdir, executable)
    if which(exe) is None:
        exe = exe[:-2] if exe.endswith('.x') else exe + '.x'
        if which(exe) is None:
            print("ERROR: Cannot find Tinker {} executable".format(executable))
            sys.exit(2)
    return exe

def which(program):
    def is_exe(fpath):
        try:
             return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
        except:
             return None
    
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    
    return None



def GenerateForceBalanceInputFile(moleculeprmfilename,qmfolderlist,liquidfolderlist,optimizefilepath,atomnumlist,liquid_equ_steps,liquid_prod_steps,liquid_timestep,liquid_interval,gas_equ_steps,gas_timestep,gas_interval,md_threads,indextogeneratecsv,qmfoldertoindex,qmfolderlisttogen,WQ_PORT,gas_prod_steps,qmrelativeweight,liqrelativeweight,enthalpyrelativeweight,densityrelativeweight):
    head,tail=os.path.split(optimizefilepath)
    newoptimizefilepath=os.path.join(os.getcwd(),tail)
    shutil.copy(optimizefilepath,newoptimizefilepath)
    temp=open(newoptimizefilepath,'r')
    results=temp.readlines()
    temp.close()
    for lineidx in range(len(results)):
        line=results[lineidx]
        linesplit=line.split()
        if 'forcefield' in line:
            if linesplit[0]=='forcefield':
                newline='forcefield '+moleculeprmfilename+'\n'
                results[lineidx]=newline
        if '$options' in line: 
            if WQ_PORT!=None:
                results.insert(lineidx+1,'WQ_PORT '+WQ_PORT+'\n') 
    temp=open(newoptimizefilepath,'a')
    liquidtargettoappend=dict(zip(liquidfolderlist,[False for i in range(len(liquidfolderlist))]))
    for i in range(len(qmfolderlist)):
        qmfolder=qmfolderlist[i]
        useqmfolder=qmfolderlisttogen[qmfolder]
        index=qmfoldertoindex[qmfolder]
        gencsv=indextogeneratecsv[index]
        atomnum=atomnumlist[index]
        if useqmfolder==True:
            results.append('$target'+'\n')
            results.append('name '+qmfolder+'\n')
            results.append('type Interaction_TINKER'+'\n')
            results.append('weight '+str(qmrelativeweight)+'\n')
            results.append('energy_denom 1.0'+'\n')
            results.append('energy_upper 10.0'+'\n')
            results.append('attenuate'+'\n')
            lastindex=str(atomnum)
            newindex=str(atomnum+1)
            lastnewindex=str(atomnum+1+2)
            homodimerlastindex=str(atomnum+atomnum)
            if 'water' in qmfolder:
                results.append('fragment1 '+'1'+'-'+lastindex+'\n')
                results.append('fragment2 '+str(newindex)+'-'+lastnewindex+'\n')
            elif 'homodimer' in qmfolder:
                results.append('fragment1 '+'1'+'-'+lastindex+'\n')
                results.append('fragment2 '+str(newindex)+'-'+homodimerlastindex+'\n')

            results.append('$end'+'\n')
        if gencsv==True:
            liquidfolder=liquidfolderlist[index] 
            value=liquidtargettoappend[liquidfolder]
            if value==False:
                liquidtargettoappend[liquidfolder]=True
                results.append('$target'+'\n')
                results.append('name '+liquidfolder+'\n')
                results.append('type Liquid_TINKER'+'\n')
                results.append('weight '+str(liqrelativeweight)+'\n')
                results.append('w_rho '+str(densityrelativeweight)+'\n')
                results.append('w_hvap '+str(enthalpyrelativeweight)+'\n')
                results.append('liquid_equ_steps '+str(liquid_equ_steps)+'\n')
                results.append('liquid_prod_steps '+str(liquid_prod_steps)+'\n')
                results.append('liquid_timestep '+str(liquid_timestep)+'\n')
                results.append('liquid_interval '+str(liquid_interval)+'\n')
                results.append('gas_equ_steps '+str(gas_equ_steps)+'\n')
                results.append('gas_prod_steps '+str(gas_prod_steps)+'\n')
                results.append('gas_timestep '+str(gas_timestep)+'\n')
                results.append('gas_interval '+str(gas_interval)+'\n')
                results.append('md_threads '+str(md_threads)+'\n')
                results.append('$end'+'\n')
    for line in results:
        temp.write(line)
    temp.close()




def ShiftVdwTypesLines(vdwtypelineslist,oldtypetonewtypelist):
    newvdwtypelineslist=[]
    for i in range(len(vdwtypelineslist)):
        newvdwtypelines=[]
        vdwtypelines=vdwtypelineslist[i]
        for vdwtypeline in vdwtypelines:
            oldtypetonewtype=oldtypetonewtypelist[i]
            linesplit=vdwtypeline.split()
            vdwtype=int(linesplit[1])
            newvdwtype=str(oldtypetonewtype[vdwtype])
            linesplit[1]=newvdwtype
            newline=' '.join(linesplit) 
            newvdwtypelines.append(newline)
        newvdwtypelineslist.append(newvdwtypelines)

    return newvdwtypelineslist 

def ShiftTypes(typeslist,oldtypetonewtypelist):
    if typeslist==None:
        return typeslist
    newtypeslist=[]
    for i in range(len(typeslist)):
        types=typeslist[i]
        oldtypetonewtype=oldtypetonewtypelist[i]
        newtypes=[]
        for ttype in types:
            ttype=int(ttype)
            newtype=str(oldtypetonewtype[ttype])
            newtypes.append(newtype)
        newtypeslist.append(newtypes) 

    return newtypeslist

def FilterHighEnergy(dimertinkerxyzfileslist,dimerenergieslist,dimersplogfileslist):
    tol=10 # kcal/mol
    Hartree2kcal_mol=627.5095
    newdimertinkerxyzfileslistoflist=[]
    newdimerenergieslistoflist=[]
    for j in range(len(dimertinkerxyzfileslist)):
        newdimertinkerxyzfileslist=[]
        newdimerenergieslist=[]

        prefixtoxyzfilelist={}
        prefixtoenergylist={}
        prefixtooriginalenergylist={}
        xyzfilelist=dimertinkerxyzfileslist[j]
        energylist=dimerenergieslist[j]
        splogfilelist=dimersplogfileslist[j]
        for i in range(len(xyzfilelist)):
            xyzfile=xyzfilelist[i]
            energy=energylist[i]
            splogfile=splogfilelist[i]
         
            filesplit=splogfile.split('_')
            filesplit=filesplit[:-2]
            prefix=''.join(filesplit)
            if prefix not in prefixtoxyzfilelist.keys():
                prefixtoxyzfilelist[prefix]=[]
                prefixtoenergylist[prefix]=[]
            prefixtoxyzfilelist[prefix].append(xyzfile)
            prefixtoenergylist[prefix].append(energy)
        for prefix,energyarray in prefixtoenergylist.items():
            normenergyarray=[i-min(energyarray) for i in energyarray]
            prefixtoenergylist[prefix]=normenergyarray
            prefixtooriginalenergylist[prefix]=energyarray

        for prefix,energyarray in prefixtoenergylist.items():
            normenergyarray=prefixtoenergylist[prefix]
            normenergyarray=[Hartree2kcal_mol*k for k in normenergyarray]
            energyarray=prefixtooriginalenergylist[prefix]
            xyzfilelist=prefixtoxyzfilelist[prefix]
            for eidx in range(len(normenergyarray)):
                e=normenergyarray[eidx]
                originale=energyarray[eidx]
                xyzfile=xyzfilelist[eidx]
                if e>=tol:
                    pass
                else:
                    newdimertinkerxyzfileslist.append(xyzfile)    
                    newdimerenergieslist.append(originale)
        newdimertinkerxyzfileslistoflist.append(newdimertinkerxyzfileslist)
        newdimerenergieslistoflist.append(newdimerenergieslist)


    return newdimertinkerxyzfileslistoflist,newdimerenergieslistoflist


def GrabNumericDensity(density_list):
    densitylist=[]
    for ls in density_list:
        if len(ls)!=0:
            for value in ls:
                if value.isnumeric():
                    break
        else:
            value=0 # this wont be used for liquid sims anyway
        densitylist.append(value)


    return densitylist


def SeperateHomoDimerAndWater(dimertinkerxyzfileslist,dimerenergieslist):
    newdimertinkerxyzfileslist=[]
    newdimerenergieslist=[]
    for i in range(len(dimertinkerxyzfileslist)):
        moldimertinkerxyzfileslist=dimertinkerxyzfileslist[i]
        moldimerenergieslist=dimerenergieslist[i]
        waterlist=[]
        homodimerlist=[]
        waterenergylist=[]
        homodimerenergylist=[]
        for j in range(len(moldimertinkerxyzfileslist)):
            xyzfile=moldimertinkerxyzfileslist[j]
            eng=moldimerenergieslist[j]
            if 'water' in xyzfile:
                waterlist.append(xyzfile)
                waterenergylist.append(eng)
            else:
                homodimerlist.append(xyzfile)
                homodimerenergylist.append(eng)      
        newlist=[waterlist,homodimerlist]
        newenergylist=[waterenergylist,homodimerenergylist]
        newdimertinkerxyzfileslist.append(newlist)
        newdimerenergieslist.append(newenergylist)  

    return newdimertinkerxyzfileslist,newdimerenergieslist


def GenerateQMFolderToCSVIndex(qmfolderlist):
    qmfoldertoindex={}
    prefixtoarray={}
    for i in range(len(qmfolderlist)):
        folder=qmfolderlist[i]
        foldersplit=folder.split('_')
        folderprefix='_'.join(foldersplit[:-1])
        if folderprefix not in prefixtoarray.keys():
            prefixtoarray[folderprefix]=[]
        prefixtoarray[folderprefix].append(folder)
    index=0
    for prefix,array in prefixtoarray.items():
        for folder in array:
            qmfoldertoindex[folder]=index
        index+=1
    return qmfoldertoindex

def CopyFilesMoveParameters(keyfilelist,molnamelist,oldtypetonewtypelist,xyzfilelist,finalxyzfilelist):
    newxyzfilelist=[]
    newkeyfilelist=[]
    newfinalxyzfilelist=[]
    for i in range(len(keyfilelist)):
        key=keyfilelist[i]
        molname=molnamelist[i]
        xyzfile=xyzfilelist[i]
        newkey=os.path.join(os.getcwd(),molname+'Gas'+'.key')
        newxyz=os.path.join(os.getcwd(),molname+'Gas'+'.xyz')
        shutil.copy(xyzfile,newxyz)
        shutil.copy(key,newkey)
        newkeyfilelist.append(newkey)
        newxyzfilelist.append(newxyz)
        finalxyz=finalxyzfilelist[i]
        head,tail=os.path.split(finalxyz)
        newfinalxyzpath=os.path.join(os.getcwd(),molname+tail)
        shutil.copy(finalxyz,newfinalxyzpath)
        newfinalxyzfilelist.append(newfinalxyzpath)
    keyfilelines=[]
    for i in range(len(newkeyfilelist)):
        newkey=newkeyfilelist[i]
        newxyz=newxyzfilelist[i]
        oldtypetonewtype=oldtypetonewtypelist[i]
        temp=open(newkey,'r')
        results=temp.readlines()
        temp.close()
        for lineidx in range(len(results)):
            line=results[lineidx]
            linesplit=line.split()
            if len(linesplit)>1:
                if linesplit[0]=='atom':
                    atomidx=lineidx
                    break
        os.remove(newkey)
        with open(newkey, 'w') as fp:
            pass  
        newresults=results[atomidx:]
        ShiftXYZTypes(newxyz,oldtypetonewtype)
        finalxyz=newfinalxyzfilelist[i]
        ShiftXYZTypes(finalxyz,oldtypetonewtype)
        for lineidx in range(len(newresults)):
            line=newresults[lineidx]
            linesplit=re.split(r'(\s+)', line) 
            willchange=False
            for eidx in range(len(linesplit)):
                e=linesplit[eidx]
                othere=e.replace('-','')
                if othere.isdigit():
                    test=int(e)
                    if test in oldtypetonewtype.keys():
                        newtype=oldtypetonewtype[test]
                        newtype=str(newtype)
                        linesplit[eidx]=newtype
                        willchange=True
            if willchange==True:
                newline=''.join(linesplit)
                newresults[lineidx]=newline
        keyfilelines.append(newresults)
         

    return newkeyfilelist,newxyzfilelist,keyfilelines,newfinalxyzfilelist


def RemoveExtraFiles():
    files=os.listdir()
    for f in files:
        if not os.path.isdir(f):
            if '.' in f and 'nohup' not in f:
                fsplit=f.split('.')
                ext=fsplit[-1]
                if ext=='key' or 'xyz' in ext or f=='xyzedit.in' or ('data' in f and 'csv' in f) or ext=='out' or ext=='prm' or ext=='arc' or ext=='dyn':
                    os.remove(f)


def ShiftXYZTypes(newxyz,oldtypetonewtype):
    temp=open(newxyz,'r')
    newresults=temp.readlines()
    temp.close()
    tempname=newxyz.replace('.xyz','_TEMP.xyz')
    temp=open(tempname,'w')
    for lineidx in range(len(newresults)):
        line=newresults[lineidx]
        linesplit=re.split(r'(\s+)', line) 
        willchange=False
        for eidx in range(len(linesplit)):
            e=linesplit[eidx]
            if e.isdigit():
                test=int(e)
                if test in oldtypetonewtype.keys():
                    newtype=oldtypetonewtype[test]
                    newtype=str(newtype)
                    linesplit[eidx]=newtype
                    willchange=True
        if willchange==True:
            line=''.join(linesplit)
        temp.write(line)
    temp.close()
    os.remove(newxyz)
    os.rename(tempname,newxyz)


def ShiftDimerXYZTypes(dimertinkerxyzfileslist,oldtypetonewtypelist):
    newdimertinkerxyzfileslist=[]
    for i in range(len(dimertinkerxyzfileslist)):
        subls=dimertinkerxyzfileslist[i]
        newsubls=[]
        oldtypetonewtype=oldtypetonewtypelist[i]
        for j in range(len(subls)):
            xyzfile=subls[j]
            head,tail=os.path.split(xyzfile)
            newxyzfile=os.path.join(os.getcwd(),tail)
            shutil.copy(xyzfile,newxyzfile)
            ShiftXYZTypes(newxyzfile,oldtypetonewtype)
            newsubls.append(newxyzfile)
        newdimertinkerxyzfileslist.append(newsubls) 

    return newdimertinkerxyzfileslist

def ReadPRMFile(prmfilepath):
    prmfilelines=[]
    temp=open(prmfilepath,'r')
    prmfilelines=temp.readlines()
    temp.close()

    return prmfilelines

def GenerateForceBalanceInputs(poltype,poltypepathlist,vdwtypeslist,liquid_equ_steps,liquid_prod_steps,liquid_timestep,liquid_interval,gas_equ_steps,gas_prod_steps,gas_timestep,gas_interval,md_threads,liquid_prod_time,gas_prod_time,WQ_PORT,csvexpdatafile,fittypestogether,vdwprmtypestofit,vdwtypestoeval,liquid_equ_time,gas_equ_time,qmrelativeweight,liqrelativeweight,enthalpyrelativeweight,densityrelativeweight,relaxFBbox):
    

    debugmode=False
    if debugmode==True:
        liquid_prod_time=.001 #ns
        gas_prod_time=.001 #ns
    
     
    gas_prod_steps=int(1000000*gas_prod_time/gas_timestep)
    liquid_prod_steps=int(1000000*liquid_prod_time/liquid_timestep)
    gas_equ_steps=int(1000000*gas_equ_time/gas_timestep)
    liquid_equ_steps=int(1000000*liquid_equ_time/liquid_timestep)

    temperature_list=None
    pressure_list=None
    enthalpy_of_vaporization_list=None
    enthalpy_of_vaporization_err_list=None
    surface_tension_list=None
    surface_tension_err_list=None
    relative_permittivity_list=None
    relative_permittivity_err_list=None
    isothermal_compressibility_list=None
    isothermal_compressibility_err_list=None
    isobaric_coefficient_of_volume_expansion_list=None
    isobaric_coefficient_of_volume_expansion_err_list=None
    heat_capacity_at_constant_pressure_list=None
    heat_capacity_at_constant_pressure_err_list=None
    density_list=None
    density_err_list=None
    citation_list=None
    nvtprops=False # NPT for most props, surface tension requires NVT and force balance complains
    addwaterprms=True
    if csvexpdatafile!=None:
        nametopropsarray=ReadCSVFile(csvexpdatafile,poltypepathlist)
        nametoarrayindexorder=GrabMoleculeOrder(poltypepathlist,nametopropsarray)
        temperature_list,pressure_list,enthalpy_of_vaporization_list,density_list=GrabArrayInputs(nametopropsarray,nametoarrayindexorder)
 
    if temperature_list==None:
        raise ValueError('No temperature data')
    if pressure_list==None:
        raise ValueError('No pressure data')
    if density_list==None:
        raise ValueError('No density data')
    
    
    CheckInputShapes([temperature_list,pressure_list,density_list])
    numberofmolecules=len(poltypepathlist)
    targetshape=ShapeOfArray(temperature_list)
    if enthalpy_of_vaporization_list==None:
        enthalpy_of_vaporization_list=GenerateNoneList(targetshape)
    
    if enthalpy_of_vaporization_err_list==None:
        enthalpy_of_vaporization_err_list=GenerateNoneList(targetshape)
    
    if surface_tension_list==None:
        surface_tension_list=GenerateNoneList(targetshape)
    
    if surface_tension_err_list==None:
        surface_tension_err_list=GenerateNoneList(targetshape)
    
    if relative_permittivity_list==None:
        relative_permittivity_list=GenerateNoneList(targetshape)
    
    if relative_permittivity_err_list==None:
        relative_permittivity_err_list=GenerateNoneList(targetshape)
    
    if isothermal_compressibility_list==None:
        isothermal_compressibility_list=GenerateNoneList(targetshape)
    
    if isothermal_compressibility_err_list==None:
        isothermal_compressibility_err_list=GenerateNoneList(targetshape)
    
    if isobaric_coefficient_of_volume_expansion_list==None:
        isobaric_coefficient_of_volume_expansion_list=GenerateNoneList(targetshape)
    
    if isobaric_coefficient_of_volume_expansion_err_list==None:
        isobaric_coefficient_of_volume_expansion_err_list=GenerateNoneList(targetshape)
    
    if heat_capacity_at_constant_pressure_list==None:
        heat_capacity_at_constant_pressure_list=GenerateNoneList(targetshape)
    
    if heat_capacity_at_constant_pressure_err_list==None:
        heat_capacity_at_constant_pressure_err_list=GenerateNoneList(targetshape)
    
    if density_list==None:
        density_list=GenerateNoneList(targetshape)
    
    if density_err_list==None:
        density_err_list=GenerateNoneList(targetshape)
    
    if citation_list==None:
        citation_list=GenerateNoneList(targetshape)
    
    listoftptopropdics=CombineData(temperature_list,pressure_list,enthalpy_of_vaporization_list,enthalpy_of_vaporization_err_list,surface_tension_list,surface_tension_err_list,relative_permittivity_list,relative_permittivity_err_list,isothermal_compressibility_list,isothermal_compressibility_err_list,isobaric_coefficient_of_volume_expansion_list,isobaric_coefficient_of_volume_expansion_err_list,heat_capacity_at_constant_pressure_list,heat_capacity_at_constant_pressure_err_list,density_list,density_err_list,citation_list)
    if poltypepathlist!=None:
        keyfilelist,xyzfilelist,dimertinkerxyzfileslist,dimerenergieslist,molnamelist,molfilelist,dimersplogfileslist,finalxyzfilelist=ReadInPoltypeFiles(poltypepathlist)
        oldtypetonewtypelist=poltype.GenerateTypeMaps(keyfilelist)
        vdwtypelineslist=GrabVdwTypeLinesFromFinalKey(keyfilelist,vdwtypeslist)
        vdwtypelineslist=ShiftVdwTypesLines(vdwtypelineslist,oldtypetonewtypelist)
        fittypestogether=ShiftTypes(fittypestogether,oldtypetonewtypelist)
        vdwtypeslist=ShiftTypes(vdwtypeslist,oldtypetonewtypelist)
        keyfilelist,xyzfilelist,keyfilelines,newfinalxyzfilelist=CopyFilesMoveParameters(keyfilelist,molnamelist,oldtypetonewtypelist,xyzfilelist,finalxyzfilelist)
        dimertinkerxyzfileslist=ShiftDimerXYZTypes(dimertinkerxyzfileslist,oldtypetonewtypelist)
        dimertinkerxyzfileslist,dimerenergieslist=FilterHighEnergy(dimertinkerxyzfileslist,dimerenergieslist,dimersplogfileslist)

        dimertinkerxyzfileslist,dimerenergieslist=SeperateHomoDimerAndWater(dimertinkerxyzfileslist,dimerenergieslist)
        indextogeneratecsv=GenerateLiquidCSVFile(nvtprops,listoftptopropdics,molnamelist)
        densitylist=GrabNumericDensity(density_list)
        prmfilepath=os.path.join(os.path.split(__file__)[0],'amoebabio18.prm')
        prmfilelines=ReadPRMFile(prmfilepath)
        optimizefilepath=os.path.join(os.path.split(__file__)[0],'optimize.in')
        xyzeditpath='xyzedit'
        analyzepath='analyze'
        if 'GPUDYNAMICS' in os.environ.keys(): # lazy gpu detection
            dynamicpath='dynamic_gpu'
            minimizepath='minimize_gpu'
        else:
            dynamicpath='dynamic'
            minimizepath='minimize'
        tinkerdir=None
        xyzeditpath=SanitizeMMExecutable(xyzeditpath,tinkerdir)
        moleculeprmfilename='molecule.prm'
        
        molprmfilepath=GenerateForceFieldFiles(vdwtypelineslist,moleculeprmfilename,fittypestogether,keyfilelines,addwaterprms,prmfilelines,vdwprmtypestofit,vdwtypestoeval,vdwtypeslist)
        rdkitmollist=GenerateRdkitMolList(molfilelist)
        atomnumlist=[rdkitmol.GetNumAtoms() for rdkitmol in rdkitmollist]
        gaskeyfilelist,gasxyzfilelist,liquidkeyfilelist,liquidxyzfilelist,datacsvpathlist=GenerateTargetFiles(keyfilelist,xyzfilelist,densitylist,rdkitmollist,prmfilepath,xyzeditpath,moleculeprmfilename,addwaterprms,molnamelist,indextogeneratecsv,keyfilelines,minimizepath,molprmfilepath,newfinalxyzfilelist,analyzepath,dynamicpath,relaxFBbox)
        liquidfolder='Liquid'
        qmfolder='QM'
        
        liquidfolderlist=GenerateLiquidTargetsFolder(gaskeyfilelist,gasxyzfilelist,liquidkeyfilelist,liquidxyzfilelist,datacsvpathlist,densitylist,liquidfolder,prmfilepath,moleculeprmfilename,vdwtypeslist,addwaterprms,molnamelist,indextogeneratecsv)
        qmfolderlist,qmfolderlisttogen=GenerateQMTargetsFolder(dimertinkerxyzfileslist,dimerenergieslist,liquidkeyfilelist,qmfolder,vdwtypeslist,molnamelist)    
        qmfoldertoindex=GenerateQMFolderToCSVIndex(qmfolderlist) # need way to keep track of liquid to QM 
        GenerateForceBalanceInputFile(moleculeprmfilename,qmfolderlist,liquidfolderlist,optimizefilepath,atomnumlist,liquid_equ_steps,liquid_prod_steps,liquid_timestep,liquid_interval,gas_equ_steps,gas_timestep,gas_interval,md_threads,indextogeneratecsv,qmfoldertoindex,qmfolderlisttogen,WQ_PORT,gas_prod_steps,qmrelativeweight,liqrelativeweight,enthalpyrelativeweight,densityrelativeweight)
        RemoveExtraFiles() 
