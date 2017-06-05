import ast
import pattern.en
import spacy
import itertools


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
                new_term = [singular_term, plural_term]

            new_terms.append(new_term)

        df['terms'].replace(terms_arrays[idx], str(new_terms), inplace=True)

    return df
