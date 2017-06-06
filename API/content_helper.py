import ast
import pattern.en
import spacy
import itertools

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


# def arrayize_term(df):
#     """
#     function that turns each row of the term column into array of arrays instead of array of strings. Here,
#     each array in the array contains just a single string.
#
#     Example: "[['term 1'], ['term 2'], ['term 3'], ...]"
#     (it is a string of array because that is what is the format originally stored in the df)
#
#     :param df: the data frame containing all the textbook content
#     :return: with modified term column as described above
#     """
#     terms_arrays = df.terms.unique()
#
#     for idx in range(0,len(terms_arrays)):
#         terms = ast.literal_eval(terms_arrays[idx])
#
#         for i in range(0, len(terms)):
#             terms[i] = [terms[i]]
#
#         df['terms'].replace(terms_arrays[idx], str(terms), inplace=True)
#
#     return df


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
        b = df['book'].unique()
        c_t = df['chapter_title'].unique()
        modules = df[df['chapter'] == c]['module'].unique()
        for m in modules:
            m_t = df['module_title'].unique()
            m_id = df['module_id'].unique()
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


def merge_terms(df):
    '''
    function to merge all terms
    :param df: dataframe representation of the textbook
    :return: an array of array of terms
    '''
    terms = []
    for row in df.index:
        terms += ast.literal_eval(df['terms'][row])
    terms = list(set(map(tuple, terms)))
    return terms

def search_sentences(df, term):
    '''
    function to search for all sentences that involve the term
    :param df:
    :param term:
    :return: an array of sentences (strings)
    '''
