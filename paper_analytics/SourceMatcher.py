from asgiref.sync import sync_to_async

from paper_manager.models import CitationStyle, Paper


class SourceMatcher:

    @staticmethod
    async def match_refs_and_sources(paper):
        """
        This method matches all found citations in the paper to be checked to the corresponding source objects.
        The source object will be saved in the reference object.
        Args:
            paper: the paper that is being checked

        Returns: nothing

        """
        paper = await Paper.objects.prefetch_related('sources', 'checks', 'checks__references').aget(pk=paper.pk)
        match paper.citation_style:
            case CitationStyle.APA:
                await SourceMatcher.match_APA(paper)
            case CitationStyle.IEEE:
                await SourceMatcher.match_IEEE(paper)
            case _:
                await SourceMatcher.match_unknown(paper)

   
    @staticmethod
    async def match_APA(paper):
        """
        This method matches the citations in the paper to be checked to the corresponding source for papers with
        the citation style APA.
        Args:
            paper: The paper that is being checked.

        Returns: nothing

        """

        # APA reference.citation_marker must have the following format:
        # (authors, year)
        
        # sort the bib entries alphabetically for the following special case:
        # x writes a paper in 2014, x and y write a paper together in 2014
        # paper by x alone must come first, so that if only the name of x ist required in the matching search, it must
        # find the paper by x alone first instead of the paper that was written by x and y, which should be matched when
        # searching for a paper that requires x and y as authors
        bib_entries = {await sync_to_async(getattr)(source,'bibliography_entry'): source for source in await sync_to_async(paper.sources.all)()}
        sorted_bib_entries = dict(sorted(bib_entries.items, key=lambda item: item[0]))
    
        # for all reference objects
        for check in await sync_to_async(paper.checks.all)():
            if check.false_positive:
                continue
            reference = await sync_to_async(getattr)(check, 'reference')
            
            # get the reference text
            reference_text = reference.citation_marker

            # remove the parentheses
            reference_text = reference_text.replace("(", "")
            reference_text = reference_text.replace(")", "")

            # the first part is about the author or authors, the part behind the comma is about the year
            authors = reference_text.partition(",")[0]
            year = reference_text.partition(",")[2]


            # if we only have one name and et al., just the one name is known, so that we can search for it
            # if two names are given with the "&", we know we have to find both
            # if only one name is given, we only have to search for that one

            # remove the et al.
            if " et al." in authors:
                authors = authors.replace(" et al.", "")
                
                # put it into an iterable list
                authors = [authors]
            # remove the and and put it into an iterable list
            elif " & " in authors:
                authors = authors.split(" & ")
            else:
                # put it into an iterable list
                authors = [authors]
            

            # remove all possible whitespaces in the year identifier
            year = ''.join(year.split())


            # try finding the right bib entry (source object) for the given reference object
            for identifier in sorted_bib_entries.keys():
                all_authors = True

                # see if all required authors are in the bibliography identifier
                for author in authors:
                    if author not in identifier:
                        all_authors = False

                # if all required authors are in the bibliography identifier and the year matches, it is the right object
                if (all_authors == True and year in identifier):
                    reference.source = sorted_bib_entries[identifier]
                    await reference.asave()

                    # as we found the right source object, we break from the inner loop
                    break
                else:
                    # else we continue our search
                    pass

    @staticmethod
    async def match_IEEE(paper):
        """
                This method matches the citations in the paper to be checked to the corresponding source for papers with
                the citation style IEEE.
                Args:
                    paper: The paper that is being checked.

                Returns: nothing

                """

        # IEEE reference.citation_marker must have the following format:
        # [number]

        # for all reference objects
        for check in await sync_to_async(paper.checks.all)():
            if check.false_positive:
                continue
            reference = await sync_to_async(getattr)(check, 'reference')
            for source in paper.sources.all():
                if reference.citation_marker == await sync_to_async(getattr)(source, 'bibliography_identifier'):
                    reference.source = source
                    await reference.asave()
                    
                    # we found the source object, so we can break from the inner loop
                    break
        return

    @staticmethod
    async def match_unknown(paper):
        """
        This method matches the citations in the paper to be checked to the corresponding source for papers with
        an unknown citation style. However, this generic matcher is not implemented yet.
        Args:
            paper: The paper that is being checked.

        Returns: nothing

        """
        # not implemented yet
        pass
