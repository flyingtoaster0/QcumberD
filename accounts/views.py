# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.template import RequestContext
from django.core.urlresolvers import reverse