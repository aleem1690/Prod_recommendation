import openai
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import json
import requests
from bs4 import BeautifulSoup
import re
import streamlit as st



class ProdRecom:
  def __init__(self):
    openai.api_key = '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'
    self._no_of_links = 2

  def req_summary(self,search_request):

    summary_model = openai.ChatCompletion.create(model='gpt-3.5-turbo',
                                            messages = [
                                                {'role':'system','content':'You are a worlds best recommendation system'},
                                                {'role':'user','content':search_request}
                                            ],
                                            functions = [
                                                {
                                                    'name':'get_product_requirements',
                                                    'description':'Identify the products based on search request',
                                                    'parameters':{
                                                        "type":"object",
                                                        "properties":{
                                                            'product_name':{
                                                                'type':'string',
                                                                'description':'identify the product the customer is looking to buy',
                                                            },
                                                            'product_price':{
                                                                'type':'string',
                                                                'description':"Identify the price & list it. if price is not mentioned specify as 'na' only",
                                                            },
                                                            'product_needs':{
                                                                'type':'string',
                                                                'description':"Identify & list down the other requirements",
                                                            },
                                                          },
                                                        "required":["product_name"],
                                                    },
                                                }
                                            ],
                                            function_call={'name':'get_product_requirements'}
                                            )

    request_summary = summary_model["choices"][0]["message"]
    return request_summary

  def result_formatting(self,summary):
    response_message = summary
    if response_message.get('function_call'):
      function_name = response_message["function_call"]["name"]
      function_dict = json.loads(response_message['function_call']['arguments'])
    for keys in function_dict:
      split_values = (function_dict[keys]).title().split(',')
      function_dict[keys]=split_values
    return function_dict

  def summary(self,search_request):
    # print(search_request)
    summary = self.req_summary(search_request)
    output = self.result_formatting(summary)
    # print(output)
    return (output)

  def links_get_text(self,url,no_of_links):
    response = requests.get(url)
    final_link_text = ''

    if response.status_code == 200:

        # print(f"Search results for '{search_item}':")
        soup = BeautifulSoup(response.text, 'html.parser')  # Parse the HTML content

        # Find all the <a> tags with 'href' attribute (links)
        all_links = soup.find_all('a', href=True)
        res_links = []
        website_dom = []

        for link in all_links:
          # print(link)

          href = link['href']
          # print(href)

          if (not href.startswith('/images')
                and not href.startswith('/search?q=related:')
                and not href.startswith('/search?q=site:')
                and 'youtube.com' not in href
                and 'video' not in href
                and 'google.com' not in href
                and 'https://' in href
                ):
                # print('done')
                # Remove "/url?q=" using regular expression
                clean_href = re.sub(r'/url\?q=', '', href)
                clean_href = re.sub(r'&ved=.*$', '', clean_href)
                # Remove unwanted '&sa=U' parameter
                clean_href = clean_href.replace('&sa=U', '')
                #Identify the domain name
                main_website = re.search('https?://([A-Za-z_0-9.-]+).*', clean_href).group(1)
                if main_website not in website_dom:
                  res_links.append(clean_href)
                  website_dom.append(main_website)
        cnt = 0
        # print(res_links)
        for pg in res_links:
          if cnt<no_of_links:
            print(cnt,'\n',pg)
            link_response = requests.get(pg)
            if link_response.status_code == 200:
              # print('200')

              link_soup = BeautifulSoup(link_response.text,'html.parser')
              for a in link_soup.findAll('a', href=True):
                a.extract()

              for img in link_soup.findAll('img', href=True):
                img.extract()

              for tg in link_soup.findAll('target_link', href=True):
                tg.extract()

              readable_text = link_soup.get_text()

              body_text = ''
              body = link_soup.find('body')
              if body:
                  body_text = body.get_text()
                  final_link_text = final_link_text+f'details of link{cnt+1}'+body_text
                  cnt +=1

    return final_link_text

  def get_google_search_results(self,summary_dict,no_of_links):
    check_prod = summary_dict['product_name']
    if len(summary_dict['product_price'])>0:
      check_price = summary_dict['product_price'][0]
    else:
      check_price = None
      
    if check_price != None:
      search_item = f'Top 10 {check_prod} under {check_price} detailed review in India'
    else:
      search_item = f'Top 10 {check_prod} detailed review in India'

    # Format the query for the URL
    search_query = search_item.replace(' ', '+')

    url = f"https://www.google.com/search?q={search_query}"
    # print(url)

    top_results_text = self.links_get_text(url,no_of_links)

    return (top_results_text)

  def get_top_products(self,results_list):


    prompt_reviews_model = openai.ChatCompletion.create(model='gpt-3.5-turbo-16k',
                                            messages = [
                                                {'role':'system','content':'You are a worlds best recommendation system'},
                                                {'role':'user','content':results_list}
                                            ],
                                            functions = [
                                                {
                                                    'name':'get_top_products',
                                                    'description':'Identify the top products based on frequency, ranking and review score in the prod_list',
                                                    'parameters':{
                                                        "type":"object",
                                                        "properties":{
                                                            'product_list':{
                                                                'type':'string',
                                                                'description':'The order of prodcuts in each link is its rank. Based on the freqeuncy of occurance, ranking & review score list the top 3 product. List only the names & no descriptions',
                                                            }
                                                          },
                                                        "required":["product_list"],
                                                    },
                                                }
                                            ],
                                            function_call={'name':'get_top_products'}
                                            )

    prompt_reviews = prompt_reviews_model["choices"][0]["message"]
    return prompt_reviews

  def get_top_reviews(self,results_dict,no_of_links):
    import nltk
    nltk.download('punkt')


    nltk.download('stopwords')
    prod_list = list(results_dict['product_list'])


    final_text = ''

    for prod in (prod_list):
      print(prod)
      search_item = f'Detailed review of {prod} in India'

      # Format the query for the URL
      search_query = search_item.replace(' ', '+')

      url = f"https://www.google.com/search?q={search_query}"
      print(url)

      top_results_text = self.links_get_text(url,no_of_links)
      final_text = final_text+top_results_text

      print(len(nltk.word_tokenize(top_results_text)),'\n',len(nltk.word_tokenize(final_text)))

    stop_words = set(stopwords.words('english'))
    words_token = word_tokenize(final_text)

    final_text_list = []

    for word in words_token:
      if word not in stop_words:
        final_text_list.append(word)

    if len(final_text_list)>14000:
      print(f'exceeding token limit by {len(final_text_list)-14000}')
      # final_text_list = final_text_list[0:14500]
      no_of_links = no_of_links-1
      final_text = get_top_reviews(results_dict,no_of_links)
      print('executed by reducing links')

    else:
      final_text = ' '.join(final_text_list)
      print(len(nltk.word_tokenize(top_results_text)),'\n',len(nltk.word_tokenize(final_text)))


    return final_text

  def final_product(self,search_request):
    summary_dict = self.summary(search_request)
    no_of_links = self._no_of_links
    google_results_text = self.get_google_search_results(summary_dict,no_of_links)
    prod_list = self.get_top_products(google_results_text)
    prod_list_dict = self.result_formatting(prod_list)
    detailed_review = self.get_top_reviews(prod_list_dict,no_of_links)

    prod_name = summary_dict['product_name']
    prod_expert = f'You are an expert in {prod_name}'
    prod_req = summary_dict['product_needs']

    final_prod_prompt = f'''
                    {prod_expert}
                    i am a customer who is looking to buy a {prod_name}. .
                    i want you to
                    1. Go through all the reviews in detail as mentioned in detailed_review.
                    2. Check & filter all {prod_name} fulfils the {prod_req}
                    3. Based on the reviews of filtered {prod_name}, and if it is fulfilling the needs identify the best {prod_name}
                    4. Under 5 sentences, justify your selection. try to relate it as close to the {prod_req}.
                    5. Give an overview instead of listing down justifications
                    6. In 2-3 sentences explain why it is better than other filtered {prod_name}

                  detailed_review: {detailed_review}

    '''
    final_prod_model = openai.ChatCompletion.create(model='gpt-3.5-turbo-16k',
                                  messages = [
                                      {"role":"system","content":prod_expert},
                                      {"role":"user","content":final_prod_prompt}
                                  ])

    final_message = final_prod_model["choices"][0]["message"]["content"]

    return final_message

# def main():
    

if __name__ == "__main__":
  # Enthusiastic welcome message
  st.title("Welcome to the Product Needs Portal!")
  st.write("Hello there! 🌟 We're excited to hear about your product needs. You can share your thoughts with us through text or voice!")

  # Radio button to select input type
  input_type = st.radio("Select input type:", ["Text", "Voice"])

  # Initialize variables
  product_needs_text = ""
  product_needs_audio = None

  #setting whisper model
  #model = whisper.load_model("base")
  #r = sr.Recognizer()

  
  if input_type == "Text":
      # Text box for sharing product needs
      user_input_text = st.text_area("What do you want to buy today?:", "")
  else:
      # Voice recording option
      st.write("We would love to hear from you!")
      # audio_bytes = audio_recorder()
      audio_bytes = audiorecorder("Click to record")

  prod_recom = ProdRecom()

  if st.button("Submit"):
      if input_type == "Text" and user_input_text.strip() != "":
        st.success("🚀 Thanks for sharing your thoughts through text!")
        user_input = user_input_text
      elif input_type == "Voice" and user_input_voice is not None:
        csuccess("🎤 Thanks for sharing your thoughts through voice!")
        user_input = user_input_voice
      else:
        st.warning("Oops! Please share your product needs, either through text or voice recording.")
      
      
      message = prod_recom.final_product(user_input)

      st.write(message)
