# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from functools import wraps
from collections import defaultdict
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.views.decorators.cache import cache_page
from django.core.exceptions import ObjectDoesNotExist
from django.template import RequestContext
from course_catalog.models import Course, Subject, Term, Section, Career, Season
import model_controls


def enforce_subject_upper(view):
    """A decorator for redirecting views to an uppercase subject URL in case
    the one provided contained lowercase characters.
    """
    cannonical_view = 'course_catalog.views.{}'.format(view.__name__)
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not kwargs['subject_abbr'].isupper():
            kwargs['subject_abbr'] = kwargs['subject_abbr'].upper()
            return redirect(cannonical_view, permanent=True, *args, **kwargs)
        return view(request, *args, **kwargs)
    return wrapped


@cache_page(60 * 30)
def index(request):
    subject_list = Subject.objects.all().order_by('abbreviation')
    max_buckets = 9

    buckets = model_controls.subject_buckets(subject_list, max_buckets)

    if buckets == None:
        return render(request, 'course_catalog/pages/index.html')
    
    return render(request, 'course_catalog/pages/index.html',
        {'subject_buckets':buckets,
         'min_height': 50 + 29 * max([len(x[1]) for x in buckets])})


@enforce_subject_upper
@cache_page(60 * 30)
def course_detail(request, subject_abbr, course_number):
    try:
        course = Course.objects.get(subject__abbreviation=subject_abbr,
                                    number=course_number)
    except ObjectDoesNotExist:
        return detail_not_found(request, subject_abbr, course_number)
    
    sections = defaultdict(list)
    for section in course.sections.all().order_by('type__order'):
        sections[section.term].append(section)

    try:
        course_data = course.course_data
    except ObjectDoesNotExist as e:
        course_data = None

    # Convert to a list of tuples for the template
    sections = sections.items()
    sections.sort(key=lambda t: t[0].order)

    return render(request, 'course_catalog/pages/course_detail.html',
        {'course': course, 'all_sections': sections, 'course_data': course_data},
        context_instance=RequestContext(request))


@enforce_subject_upper
@cache_page(60 * 30)
def subject_detail(request, subject_abbr):
    try:
        subject = Subject.objects.get(abbreviation=subject_abbr)
    except ObjectDoesNotExist:
        return detail_not_found(request, subject_abbr)

    # Since there are very few careers, we just get them all and filter later
    courses_by_career = []
    careers = Career.objects.all().order_by('order')

    for career in careers:
        c = subject.courses.filter(career=career).order_by('number')
        if c.count() != 0:
            courses_by_career.append((career, c))

    # Get seasons for the filter panel
    seasons = Season.objects.all().order_by('order')
    [setattr(s, 'checked', True) for s in seasons]

    return render(request, 'course_catalog/pages/subject_detail.html',
        {'subject': subject, 'courses_by_career': courses_by_career,
        'seasons': seasons})


def detail_not_found(request, subject_abbr, course_number=None):
    """A special 404 for pages which are probably discovered because someone
    put a bad course code in the requirements on Solus.
    """
    context = {'abbr': subject_abbr}

    if course_number is None:
        context.update({'missing': 'subject'})
    else:
        context.update({'missing': 'course', 'num': course_number})

    return render(request, 'course_catalog/pages/not_found.html', context,
        context_instance=RequestContext(request), status=404)


@cache_page(60 * 30)
def search(request):
    query = request.GET.get('q')
    results = model_controls.search_result(query)

    if isinstance(results, models.Model):
        return HttpResponseRedirect(results.get_absolute_url())

    # Otherwise, it's a list of results
    for item in results:
        if isinstance(item, Course):
            item.template_name = "course_catalog/components/course_search_result.html"
        elif isinstance(item, Subject):
            item.template_name = "course_catalog/components/subject_search_result.html"
        elif isinstance(item, Section):
            item.template_name = "course_catalog/components/section_search_result.html"

    return render(request, 'course_catalog/pages/search_results.html',
        {'results': results, 'query': query})


# TODO: All these requests should be fixed up, since they just return simple
# responses.

@cache_page(60 * 30)
def about(request):
    return render(request, 'course_catalog/text/about.html')

@cache_page(60 * 30)
def contact(request):
    return render(request, 'course_catalog/text/contact.html')

@cache_page(60 * 30)
def tos(request):
    return render(request, 'course_catalog/text/tos.html', {})

@cache_page(60 * 30)
def faqs(request):
    return render(request, 'course_catalog/text/faqs.html', {})


# Application support

@cache_page(60 * 60 * 24 *100)
def facebook_channel(request):
    return render(request, 'course_catalog/text/channel.html', {})

@cache_page(60 * 60 * 24 *100)
def flash_permissions(request):
    return HttpResponse('')

@cache_page(60 * 30)
def robots(request):
    return render(request, 'course_catalog/text/robots.txt', {})


#For testing random things

def experiments(request):
    return render(request, 'course_catalog/experiments.html', {})


def count_course_requisites(request):
    import time
    t0 = time.time()

    courses = valid = missing = 0
    all_courses = Course.objects.all()

    print('creating list of codes...')
    all_codes = [(c.subject.abbreviation, c.number) for c in all_courses]

    print('checking all requisites...')
    for course in all_courses:
        courses += 1
        for abbr, num in course.entity_requisites():
            if (abbr, num) in all_codes:
                valid += 1
            else:
                missing += 1

    tf = time.time()
    total = valid + missing
    print('done.\n')

    print('scan time: {:.1f}s'.format(tf - t0))

    print('courses scanned: {}'.format(courses))
    print('total requisites: {}'.format(total))
    print('valid requisites: {} ({:.1%})'.format(valid, valid/float(total)))
    print('missing requisites: {} ({:.1%})'.format(missing, missing/(float(total))))

    return HttpResponse('see terminal')

