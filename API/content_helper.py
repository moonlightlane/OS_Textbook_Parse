import ast
import pattern.en
import spacy
import itertools
import pandas as pd
import json
import string
import re

'''
########################################################################################################################
'''
def augment_term(df):

    df = lowercase_term(df)
    df = pluralize_term(df)

    return df


def lowercase_term(df):
    """
    function to turn all term phrases to lower cases

    :param df: the data frame containing all the textbook content
    :return: with modified term column as described above
    """
    terms_arrays = df.terms.unique()

    for idx in range(0,len(terms_arrays)):
        terms = ast.literal_eval(terms_arrays[idx])

        for i in range(0, len(terms)):
            terms[i] = terms[i].lower()

        df['terms'].replace(terms_arrays[idx], str(terms), inplace=True)

    return df


def arrayize_term(df):
    """
    function that turns each row of the term column into array of arrays instead of array of strings. Here,
    each array in the array contains just a single string.

    Example: "[['term 1'], ['term 2'], ['term 3'], ...]"
    (it is a string of array because that is what is the format originally stored in the df)

    :param df: the data frame containing all the textbook content
    :return: with modified term column as described above
    """
    terms_arrays = df.terms.unique()

    for idx in range(0,len(terms_arrays)):
        terms = ast.literal_eval(terms_arrays[idx])

        for i in range(0, len(terms)):
            terms[i] = [terms[i]]

        df['terms'].replace(terms_arrays[idx], str(terms), inplace=True)

    return df


def pluralize_term(df):
    """
    function that turns single form term into plural term or plural term into single term, where such form exist.
    In doing so, each row of the term column in the df will be modified to be array of arrays of strings, where
    each sub-array in the array is an array of strings representing multiple forms of the same term.

    Example: "[['term 1', 'term 1 plural'], ['term 2', 'term 2 plural'], ['term 3', 'term 3 plural'], ...]"
    (it is a string of array because that is what is the format originally stored in the df)

    :param df: the data frame containing all the textbook content
    :return: df: with modified term column as described above
    """
    nlp = spacy.load('en')
    terms_arrays = df.terms.unique()

    for idx in range(0, len(terms_arrays)):
        terms = ast.literal_eval(terms_arrays[idx])
        new_terms = []

        for i in range(0, len(terms)):
            # below 2 lines first convert the noun phrase to singular form and then pluralize the singularized form
            singular_term = pattern.en.singularize(terms[i])
            plural_term = pattern.en.pluralize(terms[i])
            new_term = []
            if len(terms[i].split(' ')) > 1:
                components = terms[i].split(' ')[0:-1]
                doc = nlp(unicode(terms[i]))
                for j in range(0, len(components)):
                    if doc[j].pos_ == u'NOUN':
                        temp = pattern.en.singularize(components[j])
                        components[j] = [temp, pattern.en.pluralize(temp)]
                for j in range(0, len(components)):
                    if not isinstance(components[j], list):
                        components[j] = [components[j]]
                if len(components) > 1:
                    components = list(itertools.product(*components))
                    for k in range(0, len(components)):
                        components[k] = ' '.join(list(components[k]))
                        new_term.append(components[k]+' '+singular_term.split(' ')[-1])
                        new_term.append(components[k]+' '+plural_term.split(' ')[-1])
                        if terms[i] != singular_term and terms[i] != plural_term:
                            new_term.append(components[k]+' '+terms[i].split(' ')[-1])
                else:
                    for k in range(0, len(components)):
                        new_term.append(components[0][k]+' '+singular_term.split(' ')[-1])
                        new_term.append(components[0][k]+' '+plural_term.split(' ')[-1])
                        if terms[i] != singular_term and terms[i] != plural_term:
                            new_term.append(components[0][k]+' '+terms[i].split(' ')[-1])
            else:
                if terms[i] != singular_term and terms[i] != plural_term:
                    new_term = [singular_term, plural_term, terms[i]]
                else:
                    new_term = [singular_term, plural_term]

            new_terms.append(new_term)

        df['terms'].replace(terms_arrays[idx], str(new_terms), inplace=True)

    return df



'''
########################################################################################################################
'''
def term_to_JSON(df):
    '''

    :param df: dataframe of the textbook content
    :param term: the term you want to query
    :return: a JASON representation contain the chapter of the term, the module of the term, the name of the module,
             title of the chapter, all the sentences it contains
    '''

    # collect all sentences to a single string
    content = merge_contents(df)

    # collect all terms to a single string
    terms = merge_terms(df)

    # find sentences that involve the query term
    for term in terms:
        sentences = search_sentences(content, term)
        # collect meta data info for the query term
        meta = merge_term_metadata(df, term)

    return term_info


def merge_by_chapter(df):
    '''
    function that merge all paragraphs in the textbook given the dataframe representation of the textbook
    :param df: dataframe representation of the textbook
    :return: a single string of content in the textbook, all lowercase.
    '''
    # init the data columns
    book = []
    chapter = []
    chapter_title = []
    module = []
    module_title = []
    module_id = []
    terms = []
    p_content = []

    chapters = df['chapter'].unique()
    for c in chapters:
        b = df[df['chapter']==c]['book'].unique()[0]
        c_t = df[df['chapter']==c]['chapter_title'].unique()[0]
        modules = df[df['chapter'] == c]['module'].unique()
        for m in modules:
            m_t = df[df['chapter'] == c][df['module'] == m]['module_title'].unique()[0]
            m_id = df[df['chapter'] == c][df['module'] == m]['module_id'].unique()[0]
            subset = df.loc[(df['chapter']==c) & (df['module']==m)]
            # merge content and lowercase it
            p_c = ' '.join(subset['p_content'])
            p_c = p_c.lower()
            # merge terms
            t = merge_terms(subset)
            # add to a data lists
            book.append(b)
            chapter.append(c)
            chapter_title.append(c_t)
            module.append(m)
            module_title.append(m_t)
            module_id.append(m_id)
            p_content.append(p_c)
            terms.append(t)
    # merge to dataframe
    df_copy = pd.DataFrame({'book':book,
                            'chapter':chapter,
                            'chapter_title':chapter_title,
                            'module':module,
                            'module_title':module_title,
                            'module_id':module_id,
                            'terms':terms,
                            'p_content':p_content})
    return df_copy


def original_terms(path_to_original_df):
    # read the content file
    f = path_to_original_df + 'content.csv'
    df = pd.read_csv(f)
    terms = []
    for row in df.index:
        for term in ast.literal_eval(df['terms'][row]):
            terms.append(term.lower())
    terms = list(set(terms))
        # terms = terms.unique().lower()
    return terms


def merge_terms(df):
    '''
    function to merge all terms
    :param df: dataframe representation of the textbook
    :return: an array of array of terms
    '''
    terms = []
    for row in df.index:
        if isinstance(df['terms'][row], str):
            terms += ast.literal_eval(df['terms'][row])
        elif isinstance(df['terms'][row], list):
            terms += df['terms'][row]
    terms = list(set(map(tuple, terms)))
    return terms


def coref_resolution(df, path_to_json):
    """
    function to resolve coreference
    NOTE: only replace NON-POCESSIVE PRONOUNS
    :param df: a string of content (NOTE: this df has the be chapter merged df)
    :param path_to_json: path to all json files
    :return: a string of content with coreference resolved
    """
    for row in df.index:
        # info for retrieving the relevant json file
        c = df['chapter'][row]
        m = df['module'][row]
        p_c = df['p_content'][row]
        # init config and setup for coref resolution later
        # original_len = len(p_c)
        # current_len = original_len
        # last_idx_start = 0
        # diff = 0
        idx_start_all = []
        diff_all = [] # the above two arrays should be the same length
        # import json
        data = import_json(path_to_json, c, m)
        # access coref
        corefs = data['corefs']
        sents  = data['sentences']
        # loop through all occurrences of coreferences
        for key in corefs.keys():
            # loop through each mention of each occurrence of coreferences
            for item in corefs[key]:
                # get info from each dict in the coref mention
                id_, text_, type_, number_, gender_, animacy_, \
                startIndex_, endIndex_, headIndex_, sentNum_, \
                position_, isRep_ = coref_mention_get_info(item)
                # get referred text
                if isRep_:
                    referred_text = text_
            # else replace other mentions with referred text
            for item in corefs[key]:
                # get info from each dict in the coref mention
                id_, text_, type_, number_, gender_, animacy_, \
                startIndex_, endIndex_, headIndex_, sentNum_, \
                position_, isRep_ = coref_mention_get_info(item)
                if not isRep_:
                    # only replace when the word to be replaced is a pronoun
                    if type_ == 'PRONOMINAL':
                        replace_text = text_
                        sent = sents[sentNum_-1]
                        # only replace non-poccessive pronouns
                        # if the replace_text has more than one word, only check this condition for the last word
                        if not sent['tokens'][endIndex_-2]['pos'] == 'PRP$':
                            idx_start = sent['tokens'][startIndex_-1]['characterOffsetBegin']
                            idx_end = sent['tokens'][endIndex_-2]['characterOffsetEnd']
                            if len(idx_start_all) == 0:
                                p_c = p_c[:idx_start] + referred_text + p_c[idx_end:]
                                diff = 0
                            else:
                                preceeding_start_idxs = [i for i in range(len(idx_start_all)) if \
                                                        idx_start > idx_start_all[i]]
                                diff = sum([diff_all[i] for i in preceeding_start_idxs])
                                p_c = p_c[:idx_start + diff] + referred_text + p_c[idx_end + diff:]
                            current_diff = -len(replace_text) + len(referred_text)
                            idx_start_all.append(idx_start + diff)
                            diff_all.append(current_diff)

                        # if idx_start > last_idx_start:
                        #     p_c = p_c[:idx_start+diff] + referred_text + p_c[idx_end+diff:]
                        #     last_idx_start = idx_start + diff
                        # else:
                        #     p_c = p_c[:idx_start] + referred_text + p_c[idx_end:]
                        #     last_idx_start = idx_start
                        # current_len += -len(replace_text) + len(referred_text)
                        # diff = current_len - original_len
        # change p_content to the coreference resolved version
        df['p_content'][row] = p_c
    return df


def import_json(path_to_json, c, m):
    # import JSON file
    f = path_to_json + 'content_ch_' + str(c) + '_mo_' + str(m) + '.txt.json'
    with open(f) as data_file:
        data = json.load(data_file)
    return data


def coref_mention_get_info(mention):
    id_ = mention['id']
    text_ = mention['text']
    type_ = mention['type']
    number_ = mention['number']
    gender_ = mention['gender']
    animacy_ = mention['animacy']
    startIndex_ = mention['startIndex']
    endIndex_ = mention['endIndex']
    headIndex_ = mention['headIndex']
    sentNum_ = mention['sentNum']
    position_ = mention['position']
    isRep_ = mention['isRepresentativeMention']
    return id_, text_, type_, number_, gender_, animacy_, \
           startIndex_, endIndex_, headIndex_, sentNum_, position_, isRep_


def search_sentences(content, term, json_data, embedded_terms):
    '''
    function to search for all sentences that involve the term
    :param df:
    :param term: this is an array of all possible forms of this term
    :return: an array terms (each is a string of list), and an array of dict of sentences
             corresponding to each term
    '''
    # the input term and each entry in embedded terms should all be tuples
    if type(term) != type(embedded_terms[embedded_terms.keys()[0]][0]):
        print('input term and embedded terms type does not match')
        return 0
    else:
        # check if the query term is embedded in another term
        if str(term) in embedded_terms.keys():
            EMBEDDED = True
            embedded_term = embedded_terms[str(term)]
        else:
            EMBEDDED = False
        term_sents = []
        # search in each sentence in the content
        sents = json_data['sentences']
        for sent in sents:
            APPEND = True
            # get start and end character index of the sentence
            # in order to slice a single sentence from the content
            sent_begin_idx = sent['tokens'][0]['characterOffsetBegin']
            sent_end_idx   = sent['tokens'][-1]['characterOffsetEnd']
            sent_text = content[sent_begin_idx:sent_end_idx]
            sent_dict = {'index': sent['index'], 'explicit': True, 'text': sent_text}
            # if the term is embedded in another term, want to search for the term that embeds
            # the query term. If the sentence does not contain the embedded term, then
            # append the sentence to dict
            if EMBEDDED:
                for e_t in embedded_term:
                    for e in e_t:
                        search_result = re.findall('\\b' + e + '\\b', sent_text, flags=re.IGNORECASE)
                        # change the append flag only if the embedded term does not appear in sent
                        if len(search_result) > 0:
                            # check if the sentence that contains the embedded term also contains
                            # the query term
                            for t in term:
                                search_result1 = re.findall('\\b'+t+'\\b', sent_text, flags=re.IGNORECASE)
                                if len(search_result1) >= len(search_result):
                                    APPEND = False
                        # else, attach
            # search for the query term in the sentence text
            if APPEND:
                for t in term:
                    search_result = re.findall('\\b'+t+'\\b', sent_text, flags=re.IGNORECASE)
                    if len(search_result) > 0:
                        term_sents.append(sent_dict)
        # search in corefs
        corefs = json_data['corefs']
        for key in corefs.keys():
            APPEND = True
            for item in corefs[key]:
                # get info from each dict in the coref mention
                id_, text_, type_, number_, gender_, animacy_, \
                startIndex_, endIndex_, headIndex_, sentNum_, \
                position_, isRep_ = coref_mention_get_info(item)
                # do a string match of the representative mention and the term
                if isRep_:
                    # check if the embedded term is contained in the coref text
                    if EMBEDDED:
                        for e_t in embedded_term:
                            for e in e_t:
                                search_result = re.findall('\\b' + e + '\\b', text_, flags=re.IGNORECASE)
                                # change the append flag only if the embedded term does not appear in sent
                                if len(search_result) > 0:
                                    APPEND = False
            for item in corefs[key]:
                # get info from each dict in the coref mention
                id_, text_, type_, number_, gender_, animacy_, \
                startIndex_, endIndex_, headIndex_, sentNum_, \
                position_, isRep_ = coref_mention_get_info(item)
                if not isRep_:
                    sent = sents[sentNum_ - 1]
                    sent_begin_idx = sent['tokens'][0]['characterOffsetBegin']
                    sent_end_idx = sent['tokens'][-1]['characterOffsetEnd']
                    sent_text = content[sent_begin_idx:sent_end_idx]
                    sent_dict = {'index': sent['index'],
                                 'explicit': False,
                                 'text': sent_text}
                    if APPEND:
                        search_result = re.findall('\\b' + e + '\\b', text_, flags=re.IGNORECASE)
                        if len(search_result) > 0:
                            if len(term_sents) == 0:
                                term_sents.append(sent_dict)
                            else:
                                NEW = True
                                for existing_sent in term_sents:
                                    if existing_sent['index'] == sentNum_-1:
                                        NEW = False
                                if NEW:
                                    term_sents.append(sent_dict)
        return term_sents


def query_term_in_df(df, query):
    '''
    check if a particular term exist in the df
    :param terms:
    :param query:
    :return:
    '''
    HAS_TERM = False
    chapter = []
    module_id = []
    for row in df.index:
        terms = df['terms'][row]
        if isinstance(terms, str):
            terms = ast.literal_eval(terms)
        for term in terms:
            if isinstance(term, tuple):
                for item in term:
                    if query.lower() in item.lower():
                        HAS_TERM = True
                        if df['chapter'][row] not in chapter:
                            chapter.append(df['chapter'][row])
                        if df['module_id'][row] not in module_id:
                            module_id.append(df['module_id'][row])
            elif isinstance(term, str):
                if query.lower() in term.lower():
                    HAS_TERM = True
                    if df['chapter'][row] not in chapter:
                        chapter.append(df['chapter'][row])
                    if df['module_id'][row] not in module_id:
                        module_id.append(df['module_id'][row])
    return HAS_TERM, chapter, module_id


def query_term_in_term_array(term_array, query):
    '''
    query a particular term (in the form of a string) in the term array
    (can either be a string of list or a list)
    :param term_array:
    :param query:
    :return:
    '''
    HAS_TERM = False
    PRINT = True
    if isinstance(term_array, str):
        print('string format term array input detected.')
        term_array = ast.literal_eval(term_array)
    for term in term_array:
        if isinstance(term, str):
            if PRINT:
                print('string format term detected.')
                PRINT = False
            if query.lower() in term.lower():
                HAS_TERM = True
        elif isinstance(term, tuple) or isinstance(term, list):
            if PRINT:
                print('list or tuple term format detected.')
                PRINT = False
            for item in term:
                if query.lower() in item.lower():
                    HAS_TERM = True
    return HAS_TERM


# TODO: add function to check whether the single word is surrounded by other noun phrases
def find_embedded_terms(terms):
    '''
    function to loop through the list of term arrays (each of the array contains
    variants of the particular term) and output a dict of the following format:
    {
        '["term v1","term v2", "term v3"]': [[enclosed term array 1], [enclosed term array 2]]

    }
    For example: since 'cell' is embedded in 'cell wall' and 'cell structure'
                 the following entry should be produced:
    {
        '["cell", "cells"]': [['cell wall', 'cell walls'], ['cell structure', 'cell structures']]
    }
    :param terms: a list of array of terms
    :return:
    '''
    #TODO this is a very ugly and slow implementation
    enclosed_terms = {}
    for query_term_array in terms:
        enclosed_temp = []
        for candidate_term_arrary in terms:
            # init a flag indicating whether the candidate term array contains any variants
            # in the query term array
            IS_ENCLOSED = False
            # here I made the reasonable assumption that if a term is to be enclosed in another
            # term, the length of the query term must be less than the candidate term
            # Example: length of "cell" is obviously less than "cell wall"
            if query_term_array != candidate_term_arrary and \
               len(min(query_term_array)) < len(min(candidate_term_arrary)):
                for query_term in query_term_array:
                    for candidate_term in candidate_term_arrary:
                        #TODO an ad-hoc way to remove parenthesis
                        #TODO there are terms such as "revolution theory (darvian theory)"
                        #TODO that needs a more principled way to extract things inside parenthesis
                        query_term = re.sub('[()]', '', query_term)
                        try:
                            search_result = re.findall('\\b' + query_term + '\\b',
                                                   candidate_term, flags=re.IGNORECASE)
                        except:
                            print(query_term)
                            print(candidate_term)

                        if len(search_result) > 0:
                            IS_ENCLOSED = True
                if IS_ENCLOSED:
                    enclosed_temp.append(candidate_term_arrary)
                    enclosed_terms[str(query_term_array)] = enclosed_temp
                    break

    return enclosed_terms


# TODO: more robust search function in corefs that resolves pronoun, article words
#       for example, "the results" in coref should match with "results"












































