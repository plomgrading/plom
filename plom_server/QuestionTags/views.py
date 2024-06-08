from django.shortcuts import render
from QuestionTags.services import QuestionService

def qtags_landing(request):
    service = QuestionService()
    questions = service.get_questions_with_details()
    question_count = service.get_question_count()
    context = {
        'questions': questions,
        'question_count': question_count,
    }
    return render(request, 'Questiontags/qtags_landing.html', context)

