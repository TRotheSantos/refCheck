import asyncio
import json

import django
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter

from RefCheck.settings import BASE_DIR

#sys.path.append(str(RefCheck.settings.BASE_DIR))  # needed if the IDEs project root is not the same as the django project root
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RefCheck.settings')
django.setup()

from django.core.files.base import ContentFile

from paper_retriever.services.ArxivApi import ArxivApi
from paper_retriever.services.CoreApi import CoreApi
from paper_retriever.services.CrossrefApi import CrossrefApi
from paper_retriever.services.ElsevierApi import ElsevierApi
from paper_retriever.services.SemanticScholarApi import SemanticScholarApi
from paper_retriever.services.SpringerApi import SpringerApi

import llm.models as llm_module
from paper_manager.models import Paper, Source, Author, Check
from paper_retriever.PaperImporter import PaperImporter
from paper_analytics.PaperExtractor import PaperExtractor
from paper_analytics.SourceMatcher import SourceMatcher
from paper_analytics.PaperChecker import PaperChecker


"""
Website um einfach & schnell json zu formatieren/anzuschauen:
https://jsonprettier.com/, else json.dumps(json, indent=4)
"""


# Backend test cases

def test():
    # paper = Paper.objects.get(pk=235)
    # importer = PaperImporter(paper)
    # asyncio.run(importer.embedd())
    print(llm_module.getChromaCollection("AnapayaCONNECT__The_SCION_transit_service").get())


def score_paper():
    paper, _ = setup_paper_IEEE()
    analyzer = PaperChecker(paper)
    asyncio.run(analyzer.score())


def create_check():
    paper, _ = setup_paper_IEEE()
    claim = "Path aware networking (PAN) is a promising trend in networking"
    marker = "[22]"
    type = "referenced"
    check, citation, reference = asyncio.run(Check.from_extraction(paper, 1, claim, marker, type))
    print("Created/updated: ", check, citation, reference)


def get_collections():
    # llm.models.getChromaCollection("test_paper").delete_collection()
    print("Current chroma collections: ", llm_module.client.list_collections())


def crawl_source():
    source, paper = source_from_json()
    importer = PaperImporter(paper, apis=[ArxivApi(), CoreApi(), CrossrefApi(), ElsevierApi(), SemanticScholarApi(), SpringerApi()])
    asyncio.run(importer.obtain_paper())
    print("Crawled paper: ", paper)


def source_from_json():
    # example input/output from llm
    json = {
        "reference": "[63]MingZhu,DanLi,YingLiu,DanPei,KKRamakrishnan,LiliLiu,andJianping Wu. 2015. MIFO: Multi-path Interdomain Forwarding. In Proceedings of the 44th International Conference on Parallel Processing (ICPP ’15). 180–189. https://doi.org/10.1109/ICPP.2015.27",
        "title": "MIFO: Multi-path Interdomain Forwarding",
        "authors": [
            "Ming Zhu",
            "Dan Li",
            "Ying Liu",
            "Dan Pei",
            "KK Ramakrishnan",
            "Lili Liu",
            "Jianping Wu"
        ],
        "identifier": "[63]",
        "publisher": "Proceedings of the 44th International Conference on Parallel Processing (ICPP ’15)",
        "year": 2015,
        "url": "https://doi.org/10.1109/ICPP.2015.27",
        "pages": "180–189",
        "location": "",
        "volume": "",
        "ISBN": "",
        "DOI": "10.1109/ICPP.2015.27",
        "type": "conference paper",
        "language": "en"
      }
    json = {'reference': '[53]AnapayaSystems.2021. AnapayaCONNECT:TheSCION-transitservice. https://www.anapaya.net/anapaya-connect-for-service-providers', 'title': 'AnapayaCONNECT: The SCION transit service', 'authors': [], 'identifier': '[53]', 'publisher': 'AnapayaSystems', 'year': 2021, 'url': 'https://www.anapaya.net/anapaya-connect-for-service-providers', 'pages': '', 'location': '', 'volume': '', 'ISBN': '', 'DOI': '', 'type': '', 'language': ''}


    # Setup
    paper, _ = setup_paper_IEEE()
    source, source_paper = asyncio.run(Source.from_json(paper, json, 1))
    print(f"Created Source ({source}) and corresponding Paper ({source_paper}) from json")
    return source, source_paper


# Backend paper check pipeline with automated setup
def check_paper_pipeline():
    #somehow sometimes the collection isnt passed properly to the extratcor??? just retra or use debug mode then it usually works
    # needed?
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Setup
    paper, new_file = setup_paper_IEEE()

    # Pipeline start
    if new_file:
        print("importing paper -----------------------------")
        collection, chunks = asyncio.run(PaperImporter(paper).import_paper(RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)))
        print(f"embedded {collection._collection.count()} chunks in {collection} respective {collection._collection.name}.\nPeek:\n", json.dumps(collection._collection.get(include= ["documents", "embeddings"], ids=["1", "2", "3"]), indent=4))
        extractor = PaperExtractor(paper, collection, chunks)
    else:
        extractor = PaperExtractor(paper)
    print("start analyzing -----------------------------")
    # asyncio.run(extractor.extract())
    analyzer = PaperChecker(paper)
    asyncio.run(analyzer.score())
    return None


def setup_paper_IEEE():  # only object and file, not embedding etc.
    # Simulated Userinput - configured for "uploaded" paper somewhere relatively to this file saved
    pathToPDF = BASE_DIR.joinpath("media/papers_to_test/Deployment and Scalability of an Inter-Domain Multi-Path Routing Infrastructure.pdf")
    beginningOfBibliographyString = "[1] Ashok Anand, Fahad Dogar, Dongsu Han, Boyan Li, Hyeontaek Lim, Michel Machado, Wenfei Wu, Aditya Akella, David G. Andersen, John W. Byers, Srini- vasan Seshan, and Peter Steenkiste. 2011. XIA: An Architecture for an Evolv- able and Trustworthy Internet. In Proceedings of the 10th ACM Workshop on Hot Topics in Networks (Cambridge, Massachusetts) (HotNets ’11). Association for Computing Machinery, New York, NY, USA, Article 2, 6 pages. https: //doi.org/10.1145/2070562.2070564"
    endOfBibliographyString = "[63] MingZhu,DanLi,YingLiu,DanPei,KKRamakrishnan,LiliLiu,andJianping Wu. 2015. MIFO: Multi-path Interdomain Forwarding. In Proceedings of the 44thInternationalConferenceonParallelProcessing(ICPP’15).180–189. https: //doi.org/10.1109/ICPP.2015.27"

    # Setup
    print("setting up paper -----------------------------")
    paper, created = Paper.objects.get_or_create(title="test_paper_ieee", defaults={"user_id": 1,
                                                                               "citation_style": "IEEE",
                                                                               "start_bibliography": beginningOfBibliographyString,
                                                                               "end_bibliography": endOfBibliographyString,})
    paper = Paper.objects.select_for_update().prefetch_related('authors', 'user').get(id=paper.id)
    if created or not paper.file:
        created = True
        print("Created File: ", created)
        with open(pathToPDF, 'rb') as f:
            paper.file.save("test_paper_IEEE.pdf", ContentFile(f.read()))
        f.close()
        paper.authors.add(Author.objects.get_or_create(name="test_author")[0].id)

    print("paper \"", paper, "\" set up")
    return paper, created

def setup_paper_APA():  # only object and file, not embedding etc.
    # Simulated Userinput - configured for "uploaded" paper somewhere relatively to this file saved
    # filename = "MA_Cynthia.pdf"
    # beginningOfBibliographyString = "Literaturverzeichnis Abeck, S. (2021). Web-Anwendungen und Serviceorientierte Architekturen II - Web Application Development. Forschungsgruppe Cooperation&Management Fakultät Informatik KIT. Retrieved November 22, 2021, from https://cm.tm.kit.edu/img/content/Web_Application_Development.pdf.Ajmera, Y., & Javed, A. (2021). Shared Autonomy in Web-Based Human Robot Interaction BT - Intelligent Systems and Applications (K. Arai, S. Kapoor, & R. Bhatia (eds.); pp. 696–702). Springer International Publishing."
    # endOfBibliographyString = "Zota, V. (2020). Anki Vector: Autonomer Mini-Roboter mit Charme und eigenem SDK im Test. Heise Online. Retrieved November 22, 2021, from https://www.heise.de/tests/Anki-Vector-Autonomer-Mini-Roboter-mit-Charme-und-eigenem-SDK-im-Test-4272540.html?seite=all."

    filename = "icmlapa.pdf"
    beginningOfBibliographyString = "References \nAi, X., Zhang, Z., Sun, L., Yan, J., and Hancock, E. Decompositional quantum graph neural network. arXiv preprint arXiv:2201.05158, 2022."
    endOfBibliographyString = "Quantum-based subgraph convolutional neural networks.Pattern Recognition, 88:38–49, 2019.hong, H.-S., Wang, H., Deng, Y.-H., Chen, M.-C., Peng, L.-C., Luo, Y.-H., Qin, J., Wu, D., Ding, X., Hu, Y., et al. Quantum computational advantage using photons. Science, 370(6523):1460–1463, 2020. Yung, M.-H., Casanova, J., Mezzacapo, A., Mcclean, J., Lamata, L., Aspuru-Guzik, A., and Solano, E. From transistor to trapped-ion computers for quantum chemistry. Scientific reports, 4(1):1–7, 2014."

    pathToPDF = BASE_DIR.joinpath("media/papers_to_test/" + filename)

    # Setup
    print("setting up paper -----------------------------")
    paper, created = Paper.objects.get_or_create(title="test_paper_APA", defaults={"user_id": 1,
                                                                               "citation_style": "APA",
                                                                               "start_bibliography": beginningOfBibliographyString,
                                                                               "end_bibliography": endOfBibliographyString,})
    if created or not paper.file:
        created = True
        print("Created File: ", created)
        with open(pathToPDF, 'rb') as f:
            paper.file.save("test_paper.pdf", ContentFile(f.read()))
        f.close()
        paper.authors.add(Author.objects.get_or_create(name="test_author")[0].id)

    print("set up: ", paper)
    return paper, created

def match():
    paper, _ = setup_paper_IEEE()
    # paper, _ = setup_paper_APA()
    SourceMatcher.match_refs_and_sources(paper)

# specify which tests to run
tests = [
    # test,
    # score_paper,
    check_paper_pipeline,
    # create_check,
    # source_from_json,
    # crawl_source,
    get_collections,
    # match,
]

if __name__ == "__main__":
    for test in tests:
        test()
