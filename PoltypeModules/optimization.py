import os
import sys
from socket import gethostname
from openbabel import openbabel
import re
import time
import apicall as call
import shlex
import numpy as np
import shutil
import torsiongenerator as torgen
import traceback
import warnings
from rdkit.Chem import rdmolfiles
from rdkit import Chem
from PyAstronomy import pyasl

def GeometryOPTWrapper(poltype,molist):
    optmolist=[]
    errorlist=[]
    torsionrestraintslist=[]
    totcharge=molist[0].GetTotalCharge()
    redo=False
    for molidx in range(len(molist)):
        mol=molist[molidx]
        suf=str(molidx+1)
        try:
            optmol,error,torsionrestraints = GeometryOptimization(poltype,mol,totcharge,suffix=suf)
        except:
            redo=False
            if poltype.fullopt==True:
                if poltype.pcm==True:
                     # Gaussian would have been used first if was detected. 
                     poltype.pcm=False
                     poltype.optpcm=False
                     redo=True
                else:
                    if poltype.optmethod=='MP2' and (poltype.use_gaus==False and poltype.use_gausoptonly==False) and poltype.foundgauss==True:
                        redo=True
                        poltype.use_gausoptonly=True

            if redo==True:
                shutil.copy(poltype.logoptfname,poltype.logoptfname.replace('.log','_failed.log'))
                optmolist,errorlist,torsionrestraintslist = GeometryOPTWrapper(poltype,molist) # recursive call allows for muliple attempts
            else:
                traceback.print_exc(file=sys.stdout)
                sys.exit()
        if redo==False:
            optmolist.append(optmol)
            errorlist.append(error)
            torsionrestraintslist.append(torsionrestraints)   
    return optmolist,errorlist,torsionrestraintslist
 


def CreatePsi4OPTInputFile(poltype,comfilecoords,comfilename,mol,modred,bondanglerestraints,skipscferror,chg,loose,torsionrestraints=[]):
    tempread=open(comfilecoords,'r')
    results=tempread.readlines()
    tempread.close()
    inputname=comfilename.replace('.com','.psi4')
    temp=open(inputname,'w')
    temp.write('molecule { '+'\n')
    if chg==None:
        temp.write('%d %d\n' % (mol.GetTotalCharge(), mol.GetTotalSpinMultiplicity()))
    else:
        temp.write('%d %d\n' % (chg, mol.GetTotalSpinMultiplicity()))

    for lineidx in range(len(results)):
        line=results[lineidx]
        linesplit=line.split()
        if len(linesplit)==4 and '#' not in line:
            temp.write(line)
    temp.write('}'+'\n')
    if poltype.optpcm==True:
        temp.write('set {'+'\n')
        if loose==True:
            temp.write('  g_convergence GAU_LOOSE'+'\n')
        else:
            temp.write('  g_convergence GAU'+'\n')

        temp.write('  scf_type pk'+'\n')
        temp.write('  pcm true'+'\n')
        temp.write('  pcm_scf_type total '+'\n')
        temp.write('  geom_maxiter '+str(poltype.optmaxcycle)+'\n')
        temp.write('}'+'\n')
        temp.write('pcm = {'+'\n')
        temp.write('  Units = Angstrom'+'\n')
        temp.write('  Medium {'+'\n')
        temp.write('    SolverType = IEFPCM'+'\n')
        temp.write('    Solvent = Water'+'\n')
        temp.write('  }'+'\n')
        temp.write('    Cavity {'+'\n')
        temp.write('    RadiiSet = UFF'+'\n')
        temp.write('    Type = GePol'+'\n')
        temp.write('    Scaling = False'+'\n')
        temp.write('    Area = 0.3'+'\n')
        temp.write('    Mode = Implicit'+'\n')
        temp.write('  }'+'\n')
        temp.write('}'+'\n')
    else:
        temp.write('set {'+'\n')
        temp.write('  geom_maxiter '+str(poltype.optmaxcycle)+'\n')
        if loose==True:
            temp.write('  g_convergence GAU_LOOSE'+'\n')
        else:
            temp.write('  g_convergence GAU'+'\n')

        temp.write('  dynamic_level 1'+'\n')
        temp.write('}'+'\n')

    if bondanglerestraints!=None:
        space='  '
        bondres=[bondanglerestraints[0]]
        string='frozen_distance'
        temp.write('set optking{'+'\n')
        temp.write('  '+string+' '+'='+' '+'('+'"'+'\n')
        for res in bondres:
            res=[str(i) for i in res]
            resstring=' '.join(res)+'\n'
            temp.write('   '+resstring)
        temp.write('  "'+')'+'\n')
        temp.write('}'+'\n')
       
        anglerestraints=bondanglerestraints[1:]
        string='frozen_bend'
        if len(anglerestraints)!=0:
            temp.write('set optking{'+'\n')
            temp.write('  '+string+' '+'='+' '+'('+'"'+'\n')
            for res in anglerestraints:
                res=[str(i) for i in res]
                resstring=' '.join(res)+'\n'
                temp.write('   '+resstring)
            temp.write('  "'+')'+'\n')
            temp.write('}'+'\n')
    if len(torsionrestraints)!=0:
        '''
        temp.write('set optking { '+'\n')
        temp.write('  frozen_dihedral = ("'+'\n')
        for residx in range(len(torsionrestraints)):
            res=torsionrestraints[residx]
            rta,rtb,rtc,rtd=res[:]
            if residx>0:
                temp.write(', %d %d %d %d\n' % (rta,rtb,rtc,rtd))
            else:
                temp.write('    %d %d %d %d\n' % (rta,rtb,rtc,rtd))

        temp.write('  ")'+'\n')
        temp.write('}'+'\n')
        '''

        temp.write('geometric_keywords = {'+'\n')
        temp.write(" 'coordsys' : 'tric',"+'\n')
        temp.write(" 'constraints' : {"+'\n')
        for residx in range(len(torsionrestraints)):
            res=torsionrestraints[residx]
            rta,rtb,rtc,rtd=res[:]
            angle=mol.GetTorsion(rta,rtb,rtc,rtd)
            if angle<0:
                angle=angle+360
            if residx>0:
                temp.write(" , {'type'    : 'dihedral', 'indices' : [ %d , %d , %d , %d ], 'value' : %s } \n" % (rta-1,rtb-1,rtc-1,rtd-1,str(angle)))
            else:
                temp.write(" 'set' : [{'type'    : 'dihedral', 'indices' : [ %d , %d , %d , %d ], 'value' : %s } \n" % (rta-1,rtb-1,rtc-1,rtd-1,str(angle)))

        temp.write("]"+'\n')
        temp.write("  }"+'\n')
        temp.write(" }"+'\n')


    if poltype.allowradicals==True:
        temp.write('set reference uhf '+'\n')


    temp.write('memory '+poltype.maxmem+'\n')
    temp.write('set_num_threads(%s)'%(poltype.numproc)+'\n')
    temp.write('psi4_io.set_default_path("%s")'%(poltype.scrtmpdirpsi4)+'\n')
    spacedformulastr=mol.GetSpacedFormula()
    if ('I ' in spacedformulastr):
        temp.write('    basis {'+'\n')
        temp.write('    ['+' '+poltype.optbasissetfile+' '+poltype.iodineoptbasissetfile +' '+ ']'+'\n')
        temp=ReadInBasisSet(poltype,temp,poltype.optbasissetfile,poltype.iodineoptbasissetfile)
        temp.write('    }'+'\n')
        if len(torsionrestraints)!=0:
            temp.write("optimize('%s',engine='%s',optimizer_keywords=geometric_keywords)" % (poltype.optmethod.lower(),'geometric')+'\n')
        else:
            temp.write("optimize('%s',engine='%s')" % (poltype.optmethod.lower(),'geometric')+'\n')

                                                
    else:                                       
        if len(torsionrestraints)!=0:                                        
            temp.write("optimize('%s/%s',engine='%s',optimizer_keywords=geometric_keywords)" % (poltype.optmethod.lower(),poltype.optbasisset,'geometric')+'\n')

        else:
            temp.write("optimize('%s/%s',engine='%s')" % (poltype.optmethod.lower(),poltype.optbasisset,'geometric')+'\n')

    if poltype.freq:
        temp.write('    scf_e,scf_wfn=freq("%s/%s",return_wfn=True)'%(poltype.optmethod.lower(),poltype.optbasisset)+'\n')

    temp.write('clean()'+'\n')
    temp.close()
    outputname=os.path.splitext(inputname)[0] + '.log'
    return inputname,outputname

def ReadInBasisSet(poltype,tmpfh,normalelementbasissetfile,otherelementbasissetfile):
    newtemp=open(poltype.basissetpath+normalelementbasissetfile,'r')
    results=newtemp.readlines()
    newtemp.close()
    for line in results:
        if '!' not in line:
            tmpfh.write('    '+line)


    newtemp=open(poltype.basissetpath+otherelementbasissetfile,'r')
    results=newtemp.readlines()
    newtemp.close()
    for line in results:
        if '!' not in line:
            tmpfh.write('    '+line)
    return tmpfh



def NumberInLine(poltype,line):
    numinline=False
    linesplit=line.split()
    for e in linesplit:
        try:
            float(e)
            numinline=True
        except:
            continue
            
    return numinline


def CheckIfPsi4Log(poltype,outputlog):
    check=False
    temp=open(outputlog,'r')
    results=temp.readlines()
    temp.close()
    for line in results:
        if 'Psi4' in line:
            check=True
            break 
    return check 


def GrabFinalXYZStructure(poltype,logname,filename,mol):
    checkifpsi4=CheckIfPsi4Log(poltype,logname)
    if checkifpsi4==True:
        temp=open(logname,'r')
        results=temp.readlines()
        temp.close()
        temp=open(filename,'w')
        temp.write(str(mol.NumAtoms())+'\n')
        temp.write('\n')
        finalmarker=False
        lengthchange=None
        lastsuccessidx=None
        for lineidx in range(len(results)):
            line=results[lineidx]
            if 'Successfully symmetrized geometry' in line:
                lastsuccessidx=lineidx
        if lastsuccessidx==None: # sometimes it doesnt print this but converges? 
            lastsuccessidx=len(results)-1
        for lineidx in range(len(results)):
            line=results[lineidx]
            try:
                if lineidx<lastsuccessidx:
                    if 'Geometry (in Angstrom)' in line:
                        lastidx=lineidx
            except:
                if lineidx<lastsuccessidx:
                    if 'Geometry (in Angstrom)' in line:
                        lastidx=lineidx

        for lineidx in range(len(results)):
            line=results[lineidx]
            if 'Geometry (in Angstrom)' in line and lineidx==lastidx:
                finalmarker=True
            if finalmarker==True and lineidx>lastidx:    
                linesplit=line.split()
                if (len(linesplit)!=4 and len(linesplit)!=5) and lengthchange==False:
                    lengthchange=True
                    break
                foundfloat=bool(re.search(r'\d', line))
                if (len(linesplit)==4 or len(linesplit)==5) and foundfloat==True and 'point' not in line:
                    temp.write(' '.join(line.lstrip().split()[:3+1])+'\n')
                    lengthchange=False
        temp.close()
    elif checkifpsi4==False:
        obConversion = openbabel.OBConversion()
        tempmol = openbabel.OBMol()
        inFormat = obConversion.FormatFromExt(logname)
        obConversion.SetInFormat(inFormat)
        obConversion.ReadFile(tempmol, logname)
        obConversion.SetOutFormat('xyz')
        obConversion.WriteFile(tempmol, filename)

def gen_optcomfile(poltype,comfname,numproc,maxmem,maxdisk,chkname,molecule,modred=True,torsionrestraints=[]):
    """
    Intent: Create *.com file for qm opt
    Input:
        comfname: com file name
        numproc: number of processors
        maxmem: max memory size
        chkname: chk file name
        mol: OBMol object
    Output:
        *opt-*.com is written
    Referenced By: run_gaussian
    Description: -
    """
    restraintlist = []
    write_com_header(poltype,comfname,chkname,maxdisk,maxmem,numproc)
    tmpfh = open(comfname, "a")
    if len(torsionrestraints)==0:
        modred=False
    spacedformulastr=molecule.GetSpacedFormula()
    if modred==True:
        optimizeoptlist = ["ModRedundant","maxcycles=%s"%(str(poltype.optmaxcycle)),'Loose']
    else:
        optimizeoptlist = ["Cartesian","maxcycles=%s"%(str(poltype.optmaxcycle))]

    if restraintlist:
        optimizeoptlist.insert(0,poltype.gausoptcoords)
    optstr=gen_opt_str(poltype,optimizeoptlist)
    if ('I ' in spacedformulastr):
        prevoptbasisset=poltype.optbasisset
        poltype.optbasisset='gen'
    if poltype.freq==True:
        if poltype.optpcm==True:
            optstring= "%s %s/%s freq SCRF=(PCM)" % (optstr,poltype.optmethod,poltype.optbasisset)
        else:
            optstring= "%s %s/%s freq" % (optstr,poltype.optmethod,poltype.optbasisset)
    else:
        if poltype.optpcm==True:
            optstring= "%s %s/%s SCRF=(PCM)" % (optstr,poltype.optmethod,poltype.optbasisset)
        else:
            optstring= "%s %s/%s" % (optstr,poltype.optmethod,poltype.optbasisset)
    if ('I ' in spacedformulastr):
        optstring+=' pseudo=read'
    string=' MaxDisk=%s \n'%(maxdisk)
    optstring+=string
    tmpfh.write(optstring)
    commentstr = poltype.molecprefix + " Gaussian OPT Calculation on " + gethostname()
    tmpfh.write('\n%s\n\n' % commentstr)
    tmpfh.write('%d %d\n' % (molecule.GetTotalCharge(), molecule.GetTotalSpinMultiplicity()))
    tmpfh.close()

    iteratombab = openbabel.OBMolAtomIter(molecule)
    tmpfh = open(comfname, "a")
    an = pyasl.AtomicNo()
    for atm in iteratombab:
        tmpfh.write('%2s %11.6f %11.6f %11.6f\n' % (an.getElSymbol(atm.GetAtomicNum()), atm.x(), atm.y(), atm.z()))
    tmpfh.write('\n')
    
    if ('I ' in spacedformulastr):
        formulalist=spacedformulastr.lstrip().rstrip().split()
        elementtobasissetlines=GenerateElementToBasisSetLines(poltype,poltype.basissetpath+poltype.optbasissetfile)
        for element,basissetlines in elementtobasissetlines.items():
            if element in spacedformulastr:
                for line in basissetlines: 
                    tmpfh.write(line)


        temp=open(poltype.basissetpath+poltype.iodineoptbasissetfile,'r')
        results=temp.readlines()
        temp.close()
        for line in results:
            if '!' not in line:
                tmpfh.write(line)


        
        tmpfh.write('\n')
        tmpfh.write('\n')
    tmpfh.close()
    if len(torsionrestraints)!=0:
        tempname=comfname.replace('.com','_temp.com')
        temp=open(comfname,'r')
        results=temp.readlines()
        temp.close()
        tmpfh = open(tempname, "w")
        foundatomblock=False
        writeres=False
        for k in range(len(results)):
            line=results[k]
            linesplit=line.split() 
            if len(linesplit)==4 and foundatomblock==False and '#' not in line:
                foundatomblock=True
            if len(linesplit)!=4 and foundatomblock==True and writeres==False:
                writeres=True
                tmpfh.write('\n')
                for res in torsionrestraints:
                    rta,rtb,rtc,rtd=res[:]
                    tmpfh.write('%d %d %d %d F\n' % (rta,rtb,rtc,rtd))
                tmpfh.write("\n")
            else:
                tmpfh.write(line)

        tmpfh.close()
        os.remove(comfname)
        shutil.copy(tempname,comfname)





def GenerateElementToBasisSetLines(poltype,basissetfile):
    elementtobasissetlines={}
    temp=open(basissetfile,'r')
    results=temp.readlines()
    temp.close()
    lines=[]
    for lineidx in range(len(results)):
        line=results[lineidx]
        if lineidx==0:  
            linesplit=line.split()
            element=linesplit[0]
            lines=[line]
            elementtobasissetlines[element]=lines
        elif lineidx>0 and  '****' in results[lineidx-1]:
            linesplit=line.split()
            element=linesplit[0]
            lines=[line]
            elementtobasissetlines[element]=lines
        else:
            lines.append(line)
            elementtobasissetlines[element]=lines


    return elementtobasissetlines
   
     
 
def gen_opt_str(poltype,optimizeoptlist):
    optstr = "#P opt"
    if optimizeoptlist:
        optstr += "=(" + ','.join(optimizeoptlist) + ")"
    return optstr

def write_com_header(poltype,comfname,chkfname,maxdisk,maxmem,numproc):
    """
    Intent: Add header to *.com file
    Referenced By: gen_optcomfile
    """
    tmpfh = open(comfname, "w")
    assert tmpfh, "Cannot create file: " + comfname+' '+os.getcwd()

    tmpfh.write('%RWF=' + poltype.scrtmpdirgau + '/,' + maxdisk + '\n')
    tmpfh.write("%Nosave\n")
    tmpfh.write("%Chk=" + os.path.splitext(comfname)[0] + ".chk\n")
    tmpfh.write("%Mem=" + maxmem + "\n")
    tmpfh.write("%Nproc=" + str(numproc) + "\n")
    tmpfh.close()







def gen_superposeinfile(poltype):
    """
    Intent: Initialize superpose input file (for tinker's superpose) 
    """
    poltype.WriteToLog("\n")
    poltype.WriteToLog("=========================================================\n")
    poltype.WriteToLog("Structure RMSD Comparison\n\n")
    cmd = poltype.superposeexe + ' ' + poltype.xyzoutfile + ' ' + poltype.tmpxyzfile + '_2'+' 1 N M N 0  > '+ poltype.superposeinfile
    poltype.call_subsystem([cmd],wait=True)


def CheckRMSD(poltype):
    RMSD=None
    for line in open(poltype.superposeinfile,'r'):
        if 'Root Mean' in line:
            RMSD=''
            for e in line:
                if e.isdigit() or e=='.':
                    RMSD+=e
    if RMSD!=None:   
        if float(RMSD)>poltype.maxRMSD:
            poltype.WriteToLog('Warning: RMSD of QM and MM optimized structures is high, RMSD = '+ RMSD+' Tolerance is '+str(poltype.maxRMSD))

            raise ValueError(os.getcwd()+' '+'RMSD of QM and MM optimized structures is high, RMSD = '+str(RMSD))
        else:
            poltype.WriteToLog('RMSD = '+ RMSD+' Tolerance is '+str(poltype.maxRMSD))

def StructureMinimization(poltype,torsionrestraints):
    poltype.WriteToLog("")
    poltype.WriteToLog("=========================================================")
    poltype.WriteToLog("Minimizing structure\n")
    if poltype.isfragjob==True:
        torsionrestraints=[] 
    AddTorsionRestraints(poltype,poltype.key7fname,torsionrestraints)
    cmd = poltype.minimizeexe+' -k '+poltype.tmpkeyfile+' '+poltype.tmpxyzfile+' 0.1 > Minimized_final.out'
    poltype.call_subsystem([cmd], True)

    torgen.RemoveStringFromKeyfile(poltype,poltype.key7fname,'restrain-torsion')
    torgen.RemoveStringFromKeyfile(poltype,poltype.tmpkeyfile,'restrain-torsion')


def AddTorsionRestraints(poltype,keyname,torsionrestraints):
    tmpfh=open(keyname,'a')
    for res in torsionrestraints:
        a,b,c,d=res[:]
        tmpfh.write('restrain-torsion %d %d %d %d %f\n' % (a,b,c,d,poltype.torsionrestraint))
    tmpfh.close()

def FindTorsionRestraints(poltype,mol):
    torsionrestraints=[]
    atomiter=openbabel.OBMolAtomIter(mol)
    atomnum=0
    for atom in atomiter:
        atomnum+=1
    bondnum=0
    for b in openbabel.OBMolBondIter(mol):
        t2 = b.GetBeginAtom()
        t3 = b.GetEndAtom()
        t2val=len([neighb for neighb in openbabel.OBAtomAtomIter(t2)])
        t3val=len([neighb for neighb in openbabel.OBAtomAtomIter(t3)])
        if t2val<2 or t3val<2:
            continue 
        ringbond=b.IsInRing()
        if ringbond==True:
            continue
        ls=[t2.GetIdx(),t3.GetIdx()]
        if ls in poltype.partialdoublebonds or ls[::-1] in poltype.partialdoublebonds:
            continue
        bondnum+=1
        

    if atomnum>=25 or bondnum>=2:
        for b in openbabel.OBMolBondIter(mol):
            isrot=b.IsRotor()
            t2 = b.GetBeginAtom()
            t3 = b.GetEndAtom()
            t2val=len([neighb for neighb in openbabel.OBAtomAtomIter(t2)])
            t3val=len([neighb for neighb in openbabel.OBAtomAtomIter(t3)])
            if t2val<2 or t3val<2:
                continue 
            ringbond=b.IsInRing()
            if ringbond==True:
                continue
            t2idx=t2.GetIdx()
            t3idx=t3.GetIdx()
            t2 = b.GetBeginAtom()
            t3 = b.GetEndAtom()
            t1,t4 = torgen.find_tor_restraint_idx(poltype,mol,t2,t3)

            firstangle=mol.GetAngle(t1,t2,t3)
            secondangle=mol.GetAngle(t2,t3,t4)
            atoms=[t1,t2,t3,t4]
            indices=[i.GetIdx() for i in atoms]
            if firstangle<0:
                firstangle=firstangle+360
            if secondangle<0:
                secondangle=secondangle+360
            angletol=2
            if np.abs(180-firstangle)<=3.5 or np.abs(180-secondangle)<=3.5:
                continue
            rtaatomicnum=t1.GetAtomicNum()
            rtbatomicnum=t2.GetAtomicNum()
            rtcatomicnum=t3.GetAtomicNum()
            rtdatomicnum=t4.GetAtomicNum()
            if (rtaatomicnum==7 and rtbatomicnum==7 and rtcatomicnum==7) or (rtbatomicnum==7 and rtcatomicnum==7 and rtdatomicnum==7):
                continue # sometimes nitrogens in chain very stiff double bonds then become linear during opt
            if rtbatomicnum==6:
                iteratomatom = openbabel.OBAtomAtomIter(t2)
                hcount=0
                for nrtb in iteratomatom:
                    nrtbatomicnum=nrtb.GetAtomicNum()
                    if nrtbatomicnum==1:
                        hcount+=1
                if hcount==3:
                    continue 
            if rtcatomicnum==6:
                iteratomatom = openbabel.OBAtomAtomIter(t3)
                hcount=0
                for nrtc in iteratomatom:
                    nrtcatomicnum=nrtc.GetAtomicNum()
                    if nrtcatomicnum==1:
                        hcount+=1
                if hcount==3:
                    continue
            t2idx=t2.GetIdx()
            t3idx=t3.GetIdx()
            babelfirst=[t2idx,t3idx]
            if (babelfirst in poltype.partialdoublebonds or babelfirst[::-1] in poltype.partialdoublebonds):
                continue
            t1idx=t1.GetIdx()
            t4idx=t4.GetIdx()
            torsionrestraints.append([t1idx,t2idx,t3idx,t4idx])


    return torsionrestraints

def GeometryOptimization(poltype,mol,totcharge,suffix='1',loose=False,checkbonds=True,modred=True,bondanglerestraints=None,skipscferror=False,charge=None,skiperrors=False,overridecheckterm=False): # specify charge instead of reading from mol if charge!=None
    if bondanglerestraints!=None or poltype.isfragjob==True or poltype.generateextendedconf==False: # then vdw opt
        pass
        torsionrestraints=[]
    else: # see if need to restrain torsion in extended conformation
        torsionrestraints=FindTorsionRestraints(poltype,mol)

    logoptfname=poltype.logoptfname.replace('_1','_'+suffix)
    comoptfname=poltype.comoptfname.replace('_1','_'+suffix)
    chkoptfname=poltype.chkoptfname.replace('_1','_'+suffix)

    if (poltype.use_gaus==True or poltype.use_gausoptonly==True): # try to use gaussian for opt
        term,error=poltype.CheckNormalTermination(logoptfname,errormessages=None,skiperrors=True)
        if not term or overridecheckterm==True:
            
            poltype.WriteToLog("QM Geometry Optimization")
            gen_optcomfile(poltype,comoptfname,poltype.numproc,poltype.maxmem,poltype.maxdisk,chkoptfname,mol,modred,torsionrestraints)
            cmdstr = 'GAUSS_SCRDIR=' + poltype.scrtmpdirgau + ' ' + poltype.gausexe + " " + comoptfname
            jobtooutputlog={cmdstr:os.getcwd()+r'/'+logoptfname}
            jobtolog={cmdstr:os.getcwd()+r'/'+poltype.logfname}
            scratchdir=poltype.scrtmpdirgau
            jobtologlistfilepathprefix=os.getcwd()+r'/'+'optimization_jobtolog_'+poltype.molecprefix 
            inputfilepath=os.path.join(os.getcwd(),comoptfname)
            jobtoinputfilepaths={cmdstr:[inputfilepath]}
            jobtooutputfiles={cmdstr:[logoptfname]}
            jobtoabsolutebinpath={cmdstr:poltype.which(poltype.gausexe)}
            if poltype.checkinputonly==True:
                sys.exit()
            if os.path.isfile(chkoptfname) and os.path.isfile(logoptfname):
                os.remove(logoptfname) # if chk point exists just remove logfile, there could be error in it and we dont want WaitForTermination to catch error before job is resubmitted by daemon 
            if poltype.externalapi==None:
                finishedjobs,errorjobs=poltype.CallJobsSeriallyLocalHost(jobtooutputlog,True) # have to skip errors because setting optmaxcycle to low number in gaussian causes it to crash
            else:
                if len(jobtooutputlog.keys())!=0:
                    call.CallExternalAPI(poltype,jobtoinputfilepaths,jobtooutputfiles,jobtoabsolutebinpath,scratchdir,jobtologlistfilepathprefix)
                finishedjobs,errorjobs=poltype.WaitForTermination(jobtooutputlog,False)

            cmdstr = poltype.formchkexe + " " + chkoptfname
            poltype.call_subsystem([cmdstr],True)
        term,error=poltype.CheckNormalTermination(logoptfname,errormessages=None,skiperrors=True)
        if error and term==False and skiperrors==False:
            if poltype.fullopt==True:
                poltype.RaiseOutputFileError(logoptfname) 
        optmol =  load_structfile(poltype,logoptfname)
        optmol=rebuild_bonds(poltype,optmol,mol)
        
           
    else:

        gen_optcomfile(poltype,comoptfname,poltype.numproc,poltype.maxmem,poltype.maxdisk,chkoptfname,mol,modred,torsionrestraints)
        term,error=poltype.CheckNormalTermination(logoptfname,errormessages=None,skiperrors=True)
        modred=False

        inputname,outputname=CreatePsi4OPTInputFile(poltype,comoptfname,comoptfname,mol,modred,bondanglerestraints,skipscferror,charge,loose,torsionrestraints)
        if term==False or overridecheckterm==True:
            poltype.WriteToLog("QM Geometry Optimization")
            cmdstr='psi4 '+inputname+' '+logoptfname
            jobtooutputlog={cmdstr:os.getcwd()+r'/'+logoptfname}
            jobtolog={cmdstr:os.getcwd()+r'/'+poltype.logfname}
            scratchdir=poltype.scrtmpdirpsi4
            jobtologlistfilepathprefix=os.getcwd()+r'/'+'optimization_jobtolog_'+poltype.molecprefix
            inputfilepath=os.path.join(os.getcwd(),inputname)
            jobtoinputfilepaths={cmdstr:[inputfilepath]}
            jobtooutputfiles={cmdstr:[logoptfname]}
            jobtoabsolutebinpath={cmdstr:poltype.which('psi4')}
            if poltype.checkinputonly==True:
                sys.exit()


            if os.path.isfile(logoptfname):
                os.remove(logoptfname)
            if poltype.externalapi==None:
                finishedjobs,errorjobs=poltype.CallJobsSeriallyLocalHost(jobtooutputlog,skiperrors)
            else:
                if len(jobtooutputlog.keys())!=0:
                    call.CallExternalAPI(poltype,jobtoinputfilepaths,jobtooutputfiles,jobtoabsolutebinpath,scratchdir,jobtologlistfilepathprefix)
                finishedjobs,errorjobs=poltype.WaitForTermination(jobtooutputlog,False)

        term,error=poltype.CheckNormalTermination(logoptfname,None,skiperrors) # now grabs final structure when finished with QM if using Psi4
        if error and term==False and skiperrors==False:
            if poltype.fullopt==True: # if not doing full opt, assume it did input number of cycles and check if structure is reasonable, otherwise if doing full optcheck if error and crash
                poltype.RaiseOutputFileError(logoptfname) 
        GrabFinalXYZStructure(poltype,logoptfname,logoptfname.replace('.log','.xyz'),mol)
        optmol =  load_structfile(poltype,logoptfname.replace('.log','.xyz'))
        optmol=rebuild_bonds(poltype,optmol,mol)
    optmol.SetTotalCharge(totcharge)
    GrabFinalXYZStructure(poltype,logoptfname,logoptfname.replace('.log','.xyz'),mol)
    return optmol,error,torsionrestraints


def load_structfile(poltype,structfname):
    """
    Intent: load 'structfname' as an OBMol structure
    Input:
        structfname: structure file name
    Output:
        tmpmol: OBMol object with information loaded from structfname
    Referenced By: run_gaussian, tor_opt_sp, compute_qm_tor_energy, compute_mm_tor_energy 
    Description: -
    """
    strctext = os.path.splitext(structfname)[1]
    tmpconv = openbabel.OBConversion()
    if strctext in '.fchk':
        tmpconv.SetInFormat('fchk')
    elif strctext in '.log':
        tmpconv.SetInFormat('g03')
    else:
        inFormat = openbabel.OBConversion.FormatFromExt(structfname)
        tmpconv.SetInFormat(inFormat)
    tmpmol = openbabel.OBMol()
    tmpconv.ReadFile(tmpmol, structfname)
    return tmpmol

def rebuild_bonds(poltype,newmol, refmol):

    for b in openbabel.OBMolBondIter(refmol):
        beg = b.GetBeginAtomIdx()
        end = b.GetEndAtomIdx()
        if not newmol.GetBond(beg,end):
            newmol.AddBond(beg,end, b.GetBondOrder(), b.GetFlags())
        else:
            newb=newmol.GetBond(beg,end)
            bondorder=newb.GetBondOrder()
            newb.SetBondOrder(b.GetBondOrder())

    return newmol


def PruneBonds(poltype,mol,bondtopology):
    molindexlist=[]
    atomitermol=openbabel.OBMolAtomIter(mol)
    for atom in atomitermol:
        molindexlist.append(atom.GetIdx())
    molidxtonewmolidx={}
    newmol=openbabel.OBMol() # define new OBMol object for the fragment
    atomlist=[] # list of atom objects from mol object
    newatomlist=[] # list of blank atom objects for fragment mol object
    count=1
    for index in molindexlist: # iterate over indexes in torsion
        atom=mol.GetAtom(index) # grab the atom object via index number
        molidx=atom.GetIdx()
        atomlist.append(atom) # append the atom object to list
        newatom=newmol.NewAtom()
        newatom=newatom.Duplicate(atom)
        newatomlist.append(newatom) # just put into blank atom objects
        molidxtonewmolidx[molidx]=count
        count+=1

    bondorderidxdic={} # key=(atom index1 of bond,atom index2 of bond), value=bondorder
    iterbond = openbabel.OBMolBondIter(mol) # iterator for all bond objects in the molecule
    for bond in iterbond:
        a = bond.GetBeginAtom()
        b = bond.GetEndAtom()
        aidx=a.GetIdx()
        bidx=b.GetIdx()
        if aidx in molindexlist and bidx in molindexlist: # check to make sure we want these atoms
            newaidx=molindexlist.index(aidx)+1 # new atom indexes are always in the order of atoms added to molecule via newatomlist above, +1 is because python starts at 0, atom indexes start at 1
            newbidx=molindexlist.index(bidx)+1
            bondorder=bond.GetBondOrder()
            bondorderidxdic[(newaidx,newbidx)]=bondorder

        else:
            continue

    for key in bondorderidxdic: # add back the bond between atoms in original mol object to the fragment mol object
        key=list(key)
        newaidx=key[0]
        newbidx=key[1]
        bondorder=bondorderidxdic[(newaidx,newbidx)]
        bondset=set([newaidx,newbidx])
        if bondset in bondtopology:
            newmol.AddBond(newaidx,newbidx,bondorder)

    return newmol
