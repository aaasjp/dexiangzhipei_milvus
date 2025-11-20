import os
import json
from llm.llm_service import *
from chat.chat_session import *
from chat.chat_helper import *
from retrieval.retrieve_vector_db import *
from langchain.agents import load_tools

import logging

logger = logging.getLogger(__name__)

##加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)


class ChatUitls:
    def __init__(self, llm_srv: LlmService, chat_session_manager: ChatSessionManager):
        self.llm_srv = llm_srv
        self.chat_session_manager = chat_session_manager

    def chat(self, params_dic):
        result_dic={
            'reference':'',
            'response':'',
            'recommend_questions':[],
            'reply_reference':[],
        }

        logger.info(f'请求参数: {json.dumps(params_dic, ensure_ascii=False, indent=2)}')

        prompt = params_dic['prompt']
        history = params_dic['history']
        session_id = params_dic['session_id']
        tenant_code = params_dic['tenant_code']
        collection_name = params_dic['collection_name']
        stream = params_dic['stream']
        chat_effect_params = params_dic['chat_effect_params']

        multi_chat_remember_rounds = chat_effect_params['general']['multi_chat_remember_rounds']
        open_llm_free_answer = chat_effect_params['general']['open_llm_free_answer']
        open_llm_internet_answer = chat_effect_params['general']['open_llm_internet_answer']

        qa_hit_score = chat_effect_params['knowledge']['qa_hit_score']
        qa_similar_score = chat_effect_params['knowledge']['qa_similar_score']
        doc_hit_score = chat_effect_params['knowledge']['doc_hit_score']
        rag_doc_counts = chat_effect_params['knowledge']['rag_doc_counts']

        llm_generate_params = chat_effect_params['llm_generate']

        exist = self.chat_session_manager.session_exist(session_id=session_id)
        if not exist:
            result_dic['reference'] = 'SESSION_NOT_EXIST'
            result_dic['response'] = stream_string('SESSION_NOT_EXIST', 0) if stream else 'SESSION_NOT_EXIST'
            return result_dic

        cur_round = self.chat_session_manager.get_last_round(session_id) + 1
        query = parse_text(prompt)

        '''
        ##由于是流输出，所以没法在当前轮记录下reply
        if history:
            last_string_format_answer=history[-1][-1]
            self.chat_session_manager.get_session(session_id).chat_state_history[-1].reply=last_string_format_answer
        '''
        history = history[-multi_chat_remember_rounds:]
        context_intent = summary_context_intent(query=query, history=history, llm=self.llm_srv,
                                                llm_generate_params=llm_generate_params)

        logger.info(f'当前查询: {query}, 上下文意图: {context_intent}')

        questions, answers, scores, sources = search_qa_from_vector_db(tenant_code, collection_name, query, limit=5)

        # COSINE: 越大越相似，所以使用 >= 判断
        hit_indices = [i for i, s in enumerate(scores) if scores[i] >= qa_hit_score]

        #recommend_questions = [q for i, q in enumerate(questions) if qa_similar_score < scores[i] <= qa_hit_score]
        recommend_questions=extend_questions(context_intent,llm=self.llm_srv)
        chat_stat = ChatState()
        chat_stat.round = cur_round
        chat_stat.user_question = query
        chat_stat.context_question = context_intent
        chat_stat.reply = ''

        if hit_indices:
            logger.info(f'命中QA: query={query}, context_intent={context_intent}')
            reply_reference=[{'source':'','content':answers[0]}]
            chat_stat.reply_type = 'KNOWLEDGE_QA'
            chat_stat.reply_reference = reply_reference
            chat_stat.recommend_questions = recommend_questions
            self.chat_session_manager.get_session(session_id).chat_state_history.append(chat_stat)

            reference = 'KNOWLEDGE_QA'
            response = polish_answer(answer=answers[0], llm=self.llm_srv, stream=stream,
                                     llm_generate_params=llm_generate_params)

            result_dic['recommend_questions']=recommend_questions
            result_dic['reply_reference']=reply_reference
            result_dic['reference']=reference
            result_dic['response']=response

        else:

            doc_contents, doc_scores, doc_block_ids, doc_sources, doc_file_names = \
                search_docs_block_from_vector_db(tenant_code, collection_name, context_intent,
                                                 limit=5)  ##attention,there use context_intent instead of query

            # COSINE: 越大越相似，所以使用 >= 判断
            doc_hit_indices = [i for i, s in enumerate(doc_scores) if doc_scores[i] >= doc_hit_score]
            doc_hit_indices=doc_hit_indices[0:rag_doc_counts]

            logger.info(f'文档命中索引: {doc_hit_indices}')

            if doc_hit_indices:
                logger.info(f'命中文档: query={query}, context_intent={context_intent}')

                reference_docs = [doc_contents[i] for i in doc_hit_indices if i < len(doc_contents)]
                reference_sources = [doc_sources[i] for i in doc_hit_indices if i < len(doc_sources)]
                reply_reference = [{'source':s,'content':c} for s,c in zip(reference_sources,reference_docs)]
                chat_stat.round = cur_round
                chat_stat.user_question = query
                chat_stat.context_question = context_intent
                chat_stat.reply_type = 'CONTEXT_RAG_DOC'
                chat_stat.reply = ''  ## 注意！！因为流输出，无法记录，需要在传给前端的最后一句话的时候，再记录
                chat_stat.reply_reference = reply_reference
                chat_stat.recommend_questions = recommend_questions
                self.chat_session_manager.get_session(session_id).chat_state_history.append(chat_stat)

                reference = 'CONTEXT_RAG_DOC'
                response = self.rag_docs(query, context_intent, history, reference_docs, stream=stream)

                result_dic['recommend_questions']=recommend_questions
                result_dic['reply_reference']=reply_reference
                result_dic['reference']=reference
                result_dic['response']=response
                return result_dic

            if open_llm_internet_answer=='yes':
                logger.info(f'从互联网搜索: query={query}, context_intent={context_intent}')

                chat_stat.round = cur_round
                chat_stat.user_question = query
                chat_stat.context_question = context_intent
                chat_stat.reply_type = 'CONTEXT_RAG_INTERNET'
                chat_stat.reply = ''  ## 注意！！因为流输出，无法记录，需要在传给前端的最后一句话的时候，再记录
                chat_stat.reply_reference = []
                chat_stat.recommend_questions = recommend_questions
                self.chat_session_manager.get_session(session_id).chat_state_history.append(chat_stat)

                reference = 'CONTEXT_RAG_INTERNET'

                is_succ,response = self.rag_internet(query, context_intent, history, stream=stream)
                if is_succ:
                    result_dic['recommend_questions']=recommend_questions
                    result_dic['reply_reference']=[]
                    result_dic['reference']=reference
                    result_dic['response']=response
                    return result_dic

            if open_llm_free_answer=='yes':
                logger.info(f'LLM自由回答: query={query}, context_intent={context_intent}')

                chat_stat.round = cur_round
                chat_stat.user_question = query
                chat_stat.context_question = context_intent
                chat_stat.reply_type = 'LLM_FREE_ANSWER'
                chat_stat.reply = ''  ## 注意！！因为流输出，无法记录，需要在传给前端的最后一句话的时候，再记录
                chat_stat.reply_reference = []
                chat_stat.recommend_questions = recommend_questions
                self.chat_session_manager.get_session(session_id).chat_state_history.append(chat_stat)

                reference = 'LLM_FREE_ANSWER'
                response = self.llm_srv.inference(prompt=query, history=history, stream=stream)

                result_dic['recommend_questions']=recommend_questions
                result_dic['reply_reference']=[]
                result_dic['reference']=reference
                result_dic['response']=response
                return result_dic

            logger.warning(f'无答案: query={query}, context_intent={context_intent}')

            chat_stat.round = cur_round
            chat_stat.user_question = query
            chat_stat.context_question = context_intent
            chat_stat.reply_type = 'NO_ANSWER'
            chat_stat.reply = ''  ## 注意！！因为流输出，无法记录，需要在传给前端的最后一句话的时候，再记录
            chat_stat.reply_reference = []
            chat_stat.recommend_questions = recommend_questions
            self.chat_session_manager.get_session(session_id).chat_state_history.append(chat_stat)

            reference = 'NO_ANSWER'
            response = stream_string('对不起，我没有从本地知识库中学习到此答案。')

            result_dic['recommend_questions']=recommend_questions
            result_dic['reply_reference']=[]
            result_dic['reference']=reference
            result_dic['response']=response

        return result_dic



    def rag_docs(self, query, contex_intent, history, reference_docs=[], stream=False):

        reference_content = "\n\n".join([f"- 参考资料{i}\n{cnt.strip()}" for i, cnt in enumerate(reference_docs, 1)])
        system = "## 任务\n" + \
                 "你是一个问答助手，你需要根据下面的要求来回答用户的提问\n\n" + \
                 "## 约束\n" + "- 尽量优先从下面的参考资料或者对话内容进行回答\n" + \
                 "- 如果从参考资料或者对话内容无法回答，就不要随便回答\n" + \
                 "- 回答尽量控制在200字以内\n"
        system += reference_content
        response = self.llm_srv.inference(prompt=query, system=system, history=history, stream=stream)
        return response

    def rag_internet(self, query, contex_intent, history, stream=False):
        try:
            os.environ['SERPAPI_API_KEY'] = config['SERPAPI_API_KEY']
            rag_api = load_tools(['serpapi'])[0]

            reference_content = rag_api(contex_intent)
            system = "## 任务\n" + \
                     "你是一个问答助手，你需要根据下面的要求来回答用户的提问\n\n" + \
                     "## 约束\n" + "- 尽量优先从下面的参考资料或者对话内容进行回答\n" + \
                     "- 如果从参考资料或者对话内容无法回答，就不要随便回答\n" + \
                     "- 回答尽量控制在200字以内\n"

            system += f"- 参考资料\n{reference_content}"
            response = self.llm_srv.inference(prompt=query, system=system, history=history, stream=stream)
            return True, response
        except Exception as e:
            import traceback
            logger.error(f'search from internet error:{traceback.format_exc()}')
            return False, f'search from internet error'
