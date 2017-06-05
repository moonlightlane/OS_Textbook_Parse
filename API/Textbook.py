# -*- coding: utf-8 -*-
"""
Created 18 January 2017

Will read data from files created by Andrew Waters for OpenStax textbooks

@author: Ryan Burmeister

Edit:
- Date: 21 January 2017
- Edit: Add functions to get content, questions, metadata at chapter or module level
"""

# !/usr/bin/env python

import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from nltk.stem.porter import PorterStemmer


# FixMe: I have wrong data for physics' modules
class Textbook(object):
    def __init__(self, textbook, load=True, answers=False):
        """
        :param textbooks: list of abbreviations for textbooks where
            stax-bio: Biology
            stax-phys: College Physics, nonAP
            stax-soc: Sociology,2e
        """
        # Set the precision for unit, chapter, and module information
        #pd.set_option('precision', 0) # Shouldn't need this anymore as I changed to explicity convert to ints

        self._textbook = textbook
        self._stax_dict = {'sociology': 'stax-soc',
                           'biology': 'stax-bio',
                           'physics': 'stax-phys'}
        self._tb_dir = {'sociology': '../data/sociology/',
                        'biology': '../data/biology/',
                        'physics': '../data/physics/'}
        self._answers = answers

        if load:
            self._load_data()
        else:
            self._set_metadata()
            # self._set_questions()
            self._set_content()

    def _set_questions(self):
        """
        Private function to set question data from the csv files
        Add the question data to the metadata dataframe with column,
            question: question text
        :return None
        """
        df = pd.DataFrame()

        if self._answers:
            files = ['../data/question_data_cc_full.csv', '../data/question_data_tutor_full.csv']
        else:
            files = ['../data/question_data_cc.csv', '../data/question_data_tutor.csv']

        for file in files:
            file_df_all = pd.read_csv(file)

            # lo: gives book and section location, ensure regexpr matches lo:'s at end of line as well
            file_df = file_df_all['Tags'].str.extract(r'lo:(.*?)(?:\,|$)', expand=False).str.split(':', expand=True)

            # Insert question data
            # Separate book & section, grab only the rows of data from bio, phys, soc
            file_df.columns = ['book', 'module']

            # Data which will be useful for evaluation
            file_df.insert(1, 'question', file_df_all['text'])
            file_df.insert(3, 'dok', file_df_all.Tags.str.extract(r'dok:([0-9])', expand=False))
            file_df.insert(4, 'blooms', file_df_all.Tags.str.extract(r'blooms:([0-9])', expand=False))
            if self._answers:
                file_df.insert(5, 'answer', file_df_all['Correct_Answer_Text'])

            # Lots of options (especially 5 and 6) are NaN so drop before adding
            file_df.dropna(axis=0, how='any', inplace=True)

            # Add answer options for multiple choice, a question where 'all of the above' is a possible answer
            if self._answers:
                file_df = pd.concat([file_df, file_df_all[['option_text_1', 'option_text_2',
                                                           'option_text_3', 'option_text_4',
                                                           'option_text_5', 'option_text_6']]], axis=1)

            # Only take questions from desired textbook
            file_df = file_df.loc[file_df['book'] == self._stax_dict[self._textbook]]

            # Separate section information into chapter and module information
            file_df['chapter'], file_df['module'], _ = zip(*file_df['module'].str.split('-', expand=False))

            # Remove Video Questions
            file_df = file_df[~file_df['question'].str.contains('video')]

            # Do this here instead of after compiling files as some delimiters used in preprocessing are represented in
            options = [1, 2, 3, 4, 5, 6]

            # Replace ellipsis with a comma so we can use a delimeter for fill in the blank problems
            file_df['question'] = \
                file_df['question'].str.decode('utf-8').str.replace(u'\u2026', ',').str.encode('ascii', 'ignore')

            # Replace characters in chemical equations to more readable version
            file_df['question'] = file_df['question'].str.replace('&gt;', '>')
            file_df['question'] = file_df['question'].str.replace(r'(?:<sup>|<sub>)(\d+|\+|\-)(?:</sup>|</sub>)', r'\1')

            # Remove any leftover whitespace which may have been left after
            file_df['question'] = file_df['question'].str.replace(r'[\r\n\t]', '')
            file_df['question'] = file_df['question'].str.rstrip()

            # Do same transformations on answers as on questions
            if self._answers:
                file_df['answer'] = file_df['answer'].str.replace('&gt;', '>')
                file_df['answer'] = file_df['answer'].str.replace(r'(?:<sup>|<sub>)(\d+|\+|\-)(?:</sup>|</sub>)', r'\1')
                file_df['answer'] = file_df['answer'].str.replace(r'[\r\n\t]', '')
                file_df['answer'] = file_df['answer'].str.rstrip()
                file_df['answer'] = \
                    file_df['answer'].str.decode('utf-8').str.replace(u'\u2026', ',').str.encode('ascii', 'ignore')

                # Want different columns for just the question and the question with the appended answer
                if self._answers:
                    file_df['question_and_answer'] = file_df['question']

            # Reset index to start at 0
            file_df.reset_index(inplace=True, drop=True)

            # Remove underscores for column with just the question
            file_df['question'] = file_df['question'].str.replace(r'_+', '').str.rstrip()

            #FixMe: Put all of this in separate file, way too cluttered here
            if self._answers:
                # Replace underscores in questions with correct responses, should improve semantic relationship
                for it, (question, answer) in enumerate(zip(file_df['question_and_answer'].tolist(), file_df['answer'].tolist())):
                    # Split by underscores if there are any for question so we can substitute right word
                    blanks = re.split(r'_+', question)

                    # If blank occurs at beginning or end, we don't want filter to eliminate where the blank occurred
                    if blanks[0] == '':
                        blanks[0] = '_' # Safe character as regex would have removed it in split above
                    if blanks[-1] == '': # if (not elif) because blank could be at both beginning and end
                        blanks[-1] = '_'

                    # filter removes empty string values in list, set options for multiple choice
                    blanks = filter(None, blanks)

                    # Split always returns string, if nothing to split on returns original string
                    # Ensure it actually splits on delimiter
                    if len(blanks) > 1:
                        if answer == 'all of the above': # 'all of the above' with underscores
                            answer = ''
                            for option in options:
                                answer_option = file_df.iloc[it]['option_text_%d' % option]

                                # Test for all options we do not want to include
                                # Weird way to test if option is not NaN, NaN != NaN returns True
                                # Necessary because option_text_5 and 6 are often NaN, i.e. only 4 options for question
                                # None of the above may occur after all of the above so include as option we don't want
                                if answer_option == answer_option and answer_option != 'none of the above':
                                    # Break over options if we have gotten "all of the above" or "all of these"
                                    if answer_option == 'all of the above' or answer_option == 'all of these':
                                        break
                                    answer += answer_option + ' '
                            blanks.insert(1, answer.rstrip())
                        else: # Underscores but not 'all of the above'
                            answer = re.split(',|;| and ', answer) # Known delimiters are ',' ';' and ' and '
                            for idx in range(1, len(blanks)):
                                if blanks[0] == '_':
                                    blanks = blanks[1:] # Remove blank placeholder from list
                                    blanks.insert(2*idx-2, answer[idx-1]) # 2*idx-1 to account for strings which have been added
                                else:
                                    if blanks[-1] == '_': # Remove blank placeholder from end of list
                                        blanks = blanks[:-1]
                                    blanks.insert(2*idx-1, answer[idx-1]) # 2*idx-1 to account for strings which have been added
                        question = ' '.join(blanks)
                        question = ' '.join(question.split()) # removes extra annoying spaces, i.e. double/triple spaces
                        question = re.sub(r'\s([?.!,"])', r'\1', question) # remove space before ending punctuation
                    elif answer == 'all of the above' or answer == 'all of these':
                        answer = ''
                        for option in options:
                            answer_option = file_df.iloc[it]['option_text_%d' % option]

                            # Explanation above in len(blanks)>1 section
                            if answer_option == answer_option and answer_option != 'none of the above':
                                # We have gotten all of the above or all of these
                                if answer_option == 'all of the above' or answer == 'all of these':
                                    break
                                answer += answer_option + ' '
                            question += ' ' + answer.rstrip()
                    elif answer == 'a':
                        question += ' ' + file_df.iloc[it]['option_text_1']
                    elif answer == 'b':
                        question += ' ' + file_df.iloc[it]['option_text_2']
                    elif answer == 'c':
                        question += ' ' + file_df.iloc[it]['option_text_3']
                    elif answer == 'd':
                        question += ' ' + file_df.iloc[it]['option_text_4']
                    elif answer == 'both a and b':
                        question += ' '.join([file_df.iloc[it]['option_text_1'], file_df.iloc[it]['option_text_2']])
                    elif answer == 'both b and c':
                        question += ' '.join([file_df.iloc[it]['option_text_2'], file_df.iloc[it]['option_text_3']])
                    elif answer == 'both c and d':
                        question += ' '.join([file_df.iloc[it]['option_text_3'], file_df.iloc[it]['option_text_4']])
                    elif answer == 'none of the above':
                        pass
                    elif answer == '1' or answer == '2' or answer == '3' or answer == '4' or answer == '5':
                        # Check if answer is simply a number not indicator of which answer
                        # Require 2 numbers as there must be at least 2 options for multiple choice question
                        if not re.findall(r'(\d\. .*?\d\.)', question):
                            question += ' ' + answer
                        elif answer == '1':
                            question = ' '.join(re.findall(r'(.*?)(?:1\.)(.*?)(?=\d|$)', question)[0])
                        else:
                            question = ' '.join(re.findall(r'(.*?)(?:\d\..*?)(?:{}\.)(.*?)(?=\d|$)'.format(answer), question)[0])
                    elif answer == '1 and 2' or answer == '1 and 3' or answer == '1 and 4' or answer == '2 and 3' \
                            or answer == '2 and 4' or answer == '3 and 4':
                        # Check if answer has at least two options, i.e. not simply a number
                        # FixMe: Check if all 2 choice answers always have at least 3 options or is it possible that both options are only options for some questions?
                        # FixMe: if not re.findall(r'(\d\..*?\d\..*?\d\.)', question):
                        if not re.findall(r'(\d\. .*?\d\.)', question):
                            question += ' ' + answer
                        elif answer == '1 and 2':
                            question = ' '.join(re.findall(r'(.*?)(?:1\.)(.*?)(?:2\.)(.*?)(?=\d|$)', question)[0])
                        elif answer == '1 and 3' or answer == '1 and 4':
                            answer = answer.split(' and ')
                            question = ' '.join(re.findall(r'(.*?)(?:{}\.)(.*?)(?:\d\..*?)(?:{}\.)(.*?)(?=\d|$)'.format(answer[0], answer[1]), question)[0])
                        elif answer == '2 and 3' or answer == '3 and 4':
                            answer = answer.split(' and ')
                            question = ' '.join(re.findall(r'(.*?)(?:\d\..*?)(?:{}\.)(.*?)(?:{}\..*?)(.*?)(?=\d|$)'.format(answer[0], answer[1]), question)[0])
                        elif answer == '2 and 4':
                            question = ' '.join(re.findall(r'(.*?)(?:\d\..*?)(?:2\.)(.*?)(?:\d\..*?)(?:4\.)(.*)(?=\d|$)', question)[0])
                    elif answer == '1,2,3' or answer == '1,2,4' or answer == '2,3,4':
                        # Check if answer has at least three options, i.e. not simply a number
                        # Some questions for which all 3 options are only options so just require 3 numbers to be present
                        if not re.findall(r'(\d\. .*?\d\. .*?\d\.)', question):
                            question += ' ' + answer
                        elif answer == '1,2,3':
                            question = ' '.join(re.findall(r'(.*?)(?:1\.)(.*?)(?:2\.)(.*?)(?:3\.)(.*?)(?=\d|$)', question)[0])
                        elif answer == '1,2,4':
                            question = ' '.join(re.findall(r'(.*?)(?:1\.)(.*?)(?:2\.)(.*?)(?:\d\..*?)(?:4\.)(.*?)(?=\d|$)', question)[0])
                        elif answer == '2,3,4':
                            question = ' '.join(re.findall(r'(.*?)(?:\d\..*?)(.*?)(?:2\.)(.*?)(?:3\.)(.*?)(?:4\.)(.*?)(?=\d|$)', question)[0])
                    else:
                        question += ' ' + answer

                    # Set the question to the new question with the answer
                    file_df.set_value(it, 'question_and_answer', question)

                # Remove this math text after as underscores also signify blank spaces to be filled
                file_df['question_and_answer'] = \
                    file_df['question_and_answer'].str.decode('utf-8').str.replace(u'\u2026', ',').str.encode('ascii', 'ignore')
                file_df['option_text_%d' % option] = file_df['option_text_%d' % option].str.replace('&gt;', '>')
                file_df['question_and_answer'] = \
                    file_df['question_and_answer'].str.replace(r'(?:<sup>|<sub>)(\d+|\+|\-)(?:</sup>|</sub>)', r'\1')
                file_df['question_and_answer'] = \
                    file_df['question_and_answer'].str.replace(r'<span data-math="(.*?)"></span>', r'\1').str.replace(r'_|\^', '').str.replace(r'\\text{(.*?)}', r'\1')

                # Remove any leftover whitespace which may have been left at end
                file_df['question_and_answer'] = file_df['question_and_answer'].str.replace(r'\r\n', '') # Sometimes occurs before end of question
                file_df['question_and_answer'] = file_df['question_and_answer'].str.replace(r'\t', '')
                file_df['question_and_answer'] = file_df['question_and_answer'].str.rstrip()

                # decode/encode for updated question in case any unicode not specifically addressed is added by answer responses
                file_df['question_and_answer'] = file_df['question_and_answer'].str.decode('utf-8').str.encode('ascii', 'ignore')

                # Don't need the answer options anymore; Correct have been included if self._answers is True
                for option in options:
                    del file_df['option_text_%d' % option]

            # Apply the same conversions above to each of the questions
            file_df['question'] = \
                file_df['question'].str.replace(r'(?:<sup>|<sub>)(\d+|\+|\-)(?:</sup>|</sub>)', r'\1')
            file_df['question'] = \
                file_df['question'].str.replace(r'<span data-math="(.*?)"></span>', r'\1').str.replace(r'_|\^', '').str.replace(r'\\text{(.*?)}', r'\1')

            # Concatenate multiple file dataframes together
            df = pd.concat([df, file_df], axis=0)

        # Drop any duplicate questions (same question in cc and tutor)
        df.drop_duplicates(keep='first', inplace=True)

        # Reset index to begin at 0
        df.reset_index(drop=True, inplace=True)

        # Reorder columns for pretty file
        if self._answers:
            df = df[['book', 'chapter', 'module', 'dok', 'blooms', 'question', 'question_and_answer']]
        else:
            df = df[['book', 'chapter', 'module', 'dok', 'blooms', 'question']]

        # Will be how data is loaded in from the file, so change if not loading from original data files
        df['chapter'] = df['chapter'].astype(int)
        df['module'] = df['module'].astype(int)
        df['dok'] = df['module'].astype(int)
        df['blooms'] = df['blooms'].astype(int)

        # Merge question and metadata
        self._questions = pd.merge(self._metadata, df, how='left', on=['book', 'chapter', 'module'])
        self._questions.dropna(axis=0, how='any', inplace=True)

    def _set_metadata(self):
        """
        Private function to set a mapping of the metadata from of the textbooks
        Sets the metadata dataframe with columns
            book: list of abbreviations for textbooks where
                stax-bio: Biology
                stax-phys: College Physics, nonAP
                stax-soc: Sociology,2e
            chapter: chapter number
            module: module number
            chapter_tile: title of chapter
            module_tile: title of module
            module_id: id of directory containing files for module
        :return None
        """
        module_dict = {'sociology': '../data/sociology/sociology_modules.csv',
                       'biology': '../data/biology/biology_modules.csv',
                       'physics': '../data/physics/physics_modules.csv'}

        df = pd.read_csv(module_dict[self._textbook])
        df.insert(0, 'book', self._stax_dict[self._textbook])

        # Only stax-phys has this column
        if 'unit' in df: df.drop('unit', axis=1, inplace=True)

        # Set up dataframe, add column for module, remove chapter and module from module_tile
        df.insert(2, 'module', df.module_title.str.extract(r'\.(\d)', expand=False))
        df['module_title'] = df.module_title.str.replace(r'.+? ', '', n=1)
        df.rename(columns={'chapter_number': 'chapter'}, inplace=True)  # to match the question data

        # Done for biology unit lines and physics appendix lines
        df.dropna(axis=0, how='any', inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Will be how data is loaded in, so change if not loading
        df['chapter'] = df['chapter'].astype(int)
        df['module'] = df['module'].astype(int)

        self._metadata = df

    def _set_content(self):
        """
        Private function to set the content of the textbooks
        Path ordering: textbook_directory/module_directory/index.cnxml.html
        Sets the content dataframe with columns
            book: list of abbreviations for textbooks where
                stax-bio: Biology
                stax-phys: College Physics, nonAP
                stax-soc: Sociology,2e
            module_id: id of directory containing files for module
            terms: any specified terms with definitions within paragraph
            p_id: id of paragraph from which text is taken
            p_content: paragraph content
        :return None
        """
        # FixMe: Need to adapt _getContent for stax-phys textbook
        paragraph_info = []
        tb_dir = self._tb_dir[self._textbook]
        module_dir_list = [dir for dir in os.listdir(tb_dir) if os.path.isdir(os.path.join(tb_dir, dir))]

        stemmer = PorterStemmer() # used to trim plural terms in definitions

        for module_dir in module_dir_list:
            soup = BeautifulSoup(open(tb_dir + module_dir + '/index.cnxml.html'), 'lxml')
            module_par_info = []
            for p in soup.find_all('p'):
                try:
                    # remove class in parent tag indicating data not found in with typical paragraph sections
                    bad_class = {'problem', 'solution', 'references', 'further-research', 'interactive',
                                 'art-connection'}
                    parent_class = p.parent.attrs['class']
                    if set(parent_class).isdisjoint(bad_class):
                        module_par_info.append([self._stax_dict[self._textbook], module_dir,
                                                p['id'], p.getText().encode('ascii', 'ignore')])
                except KeyError:
                    # Ensure that we still get paragraph material without the "bad class" attributes in parents
                    module_par_info.append([self._stax_dict[self._textbook], module_dir, p['id'],
                                            p.getText().encode('ascii', 'ignore')])

            # Get all of the paragraph text
            pars = [info[-1] for info in module_par_info]

            # Append any html list which may be part of paragraph in textbook
            regex = re.compile(r'\n')
            for ol in soup.find_all('ol'):
                prev_par = ol.findPrevious('p').getText().encode('ascii', 'ignore')
                if prev_par in pars:
                    index = pars.index(prev_par)
                    module_par_info[index][-1] = '{0} {1}'.format(pars[index],
                                                                  regex.sub(' ', ol.getText().encode('ascii',
                                                                                                     'ignore')))

            # Find all of the terms with definitions
            # FixMe: change term extraction from selecting highlighted phrases in text to extracting terms in metadata
            # terms = [[] for _ in range(len(module_par_info))]
            # print terms
            # for span in soup.find_all('span'):
            #     if span['data-type'] == 'term' and span.parent.name == 'p':
            #         par_index = pars.index(span.parent.getText().encode('ascii', 'ignore'))
            #         # Stem each word in term and rejoin into one string
            #         # terms[par_index].append(span.getText().encode('ascii', 'ignore').lower().replace(',', ''))
            #         terms[par_index].append(' '.join([stemmer.stem(word) for word in span.getText().encode('ascii', 'ignore').lower().replace(',', '').split()]))
            for meta in soup.find_all('meta'):
                if meta['name'] == 'keywords':
                    terms = meta['content'].encode('ascii', 'ignore')
                    terms = terms.split(', ')
            for i in range(len(module_par_info)):
                # Insert so that the csv is pleasant to look at, p_id and paragraph text will run over otherwise
                module_par_info[i].insert(2, terms)

            paragraph_info += module_par_info

        self._content = pd.merge(self._metadata,
                                 pd.DataFrame(paragraph_info,
                                              columns=['book', 'module_id', 'terms', 'p_id', 'p_content']),
                                 how='left', on=['book', 'module_id'])

        # Introduction directories do not have any content which is kept
        self._content.dropna(axis=0, how='any', inplace=True)

        # Only keep content which is not empty
        self._content = self._content[(self._content['p_content'] != '')]

        # Decode so hex, new line, and carriage return characters are replaced
        self._content['p_content'] = self._content['p_content'].str.replace(r'_+', '')
        self._content['p_content'] = (self._content['p_content'].str.decode('utf-8')).str.encode('ascii', 'ignore')

    def _load_data(self):
        """
        Loads data from content and question csv files saved into textbook directory
        Will load metadata from the same file as when creating csv files
        :return None
        """
        self._set_metadata()
        self._content = pd.read_csv('%s/content.csv' % self._tb_dir[self._textbook])

        if self._answers:
            self._questions = pd.read_csv('%s/questions_and_answers.csv' % self._tb_dir[self._textbook])
        else:
            self._questions = pd.read_csv('%s/questions.csv' % self._tb_dir[self._textbook])

    def get_questions(self):
        """
        :return: dataframe of all questions content
        """
        return self._questions

    def get_content(self):
        """
        :return: dataframe of all textbook content
        """
        return self._content

    def to_csv(self):
        """
        Writes the content and question data to the textbook directory
        Content data is written to textbook_directory/content.csv
        Question data is written to textbook_directory/questions.csv
        :return None
        """
        self._content.to_csv(path_or_buf='%s/content.csv' % self._tb_dir[self._textbook])

        # if self._answers:
        #     self._questions.to_csv(path_or_buf='%s/questions_and_answers.csv' % self._tb_dir[self._textbook])
        # else:
        #     self._questions.to_csv(path_or_buf='%s/questions.csv' % self._tb_dir[self._textbook])

    def get_chapter(self, chapter):
        """
        Gets the content and questions material from the requested chapter
        :param chapter: chapter number
        :return: two dataframes
            content: content data
            questions: question data
        """
        content = pd.DataFrame(self._content.loc[self._content['chapter'] == int(chapter),
                                                 ['p_content', 'terms', 'module', 'module_id']]).reset_index(drop=True)
        if self._answers:
            questions = pd.DataFrame(self._questions.loc[self._questions['chapter'] == int(chapter),
                                                         ['question', 'question_and_answer', 'module', 'module_id',
                                                          'dok', 'blooms']]
                                     ).reset_index(drop=True)
        else:
            questions = pd.DataFrame(self._questions.loc[self._questions['chapter'] == int(chapter),
                                                         ['question', 'module', 'module_id', 'dok', 'blooms']]
                                     ).reset_index(drop=True)

        return content, questions

    def get_module(self, chapter, module):
        """
        Gets the content and questions material from the requested chapter and module
        :param chapter: chapter number
        :param module: module number
        :return: two dataframes
            content: content data
            questions: question data
        """
        content = pd.DataFrame(self._content.loc[(self._content['chapter'] == int(chapter)) &
                                                 (self._content['module'] == int(module)), ['p_content', 'terms']]
                               ).reset_index(drop=True)

        if self._answers:
            questions = pd.DataFrame(self._questions.loc[(self._questions.chapter == int(chapter)) &
                                                         (self._questions.module == int(module)),
                                                         ['question', 'question_and_answer', 'module_id',
                                                          'dok', 'blooms']]
                                     ).reset_index(drop=True)
        else:
            questions = pd.DataFrame(self._questions.loc[(self._questions.chapter == int(chapter)) &
                                                         (self._questions.module == int(module)),
                                                         ['question', 'module_id', 'dok', 'blooms']]
                                     ).reset_index(drop=True)

        return content, questions

    def get_chapter_set(self):
        """
        Get the set of chapter numbers within the textbook
        :return: set of chapters
        """
        return set(self._questions['chapter'].tolist())

    def get_module_set(self, chapter):
        """
        Get the set of modules numbers for the specified chapter of the textbook
        :return: set of modules
        """
        return set((self._questions.loc[self._questions['chapter'] == int(chapter), 'module']).tolist())
