jQuery= jQuery.noConflict();

var url_base = "http://rhetoric.metadada.xyz/phrase/";

function qs_param(name, url) {
    if (!url) {
      url = window.location.href;
    }
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}

function stripped(s) {
  s = s.replace(/\W/g, '');
  return s.toLowerCase();
}

function normalize_phrase(eles, next_ele) {
  var words = [];
  for (var i=0; i<eles.length; i++) {
    var w = stripped(eles[i].text());
    if (w!="") {
      words.push(w);
    }
  }
  if (next_ele) {
    var w = stripped(next_ele.text());
    if (w!="") {
      words.push(w);
    }
  }
  return words;
}

function get_phrase(words) {
  var normalized = normalize_phrase(words, false);
  for (var i=0; i<phrases.length; i++) {
    var idx = 0;
    var found = true;
    var split = phrases[i].split(' ');
    
    if (split.length==normalized.length) {
      for (var j=0; j<normalized.length; j++) {
        if (j<split.length && normalized[j]==split[j]) {
          // nothing
        } else {
          found = false;
        }
      }
      if (found ) {
        return phrases[i];
      }
    }
  }
  return false;
}

function continues_phrase(words, next_word) {
  var normalized = normalize_phrase(words, next_word);
  if (normalized.length==0) {
    return false;
  }
  
  for (var i=0; i<phrases.length; i++) {
    var idx = 0;
    var found = true;
    var split = phrases[i].split(' ');
    
    for (var j=0; j<normalized.length; j++) {
      if (j<split.length && normalized[j]==split[j]) {
        // nothing
      } else {
        found = false;
      }
    }
    if (found) {
      return phrases[i];
    }
  }
  return false;
}

jQuery(document).ready(function($){

    function convert_candidates_to_link($eles, selector ,phrase) {
      var search_for = qs_param('search');
      var str = [];
      for (var i=0; i<$eles.length; i++) {
        str.push($eles[i].text());
        //$(this).contents().unwrap();
      }
      var $a = $('<a>',{
          title: 'who else says "'+phrase+'"?',
          href: url_base+phrase,
          target: '_blank',
          class: 'rhetoric'
      })
      if (search_for && search_for==phrase) {
        $a.addClass('found');
      }
      $(selector).wrapAll( $a ).parent().text(str.join(' '));
    }

    function consider_word($candidates, $word) {
      var possible_phrase = continues_phrase($candidates, $word);
      if (possible_phrase) {
        // does adding the word still produce a valid candidate phrase?
        $candidates.push($word);
        $word.addClass('candidate');
        return $candidates;
      } else {
        var valid_phrase = get_phrase($candidates);
        // do the candidates add up to a whole valid phrase on their own?
        if (valid_phrase) {
          convert_candidates_to_link($candidates, '.candidate' , valid_phrase);
          $('.candidate').removeClass('candidate');
          return [];
        // ok, can we start a new phrase with the current word?
        } else if ($candidates.length==1) {
          $('.candidate').removeClass('candidate');
          return consider_word([], $word);
        } else {
          $('.candidate').removeClass('candidate');
          return [];
        }
      }
    }

    $('.speech p,dd').each(function(ele) {
      // 1. Wrap every word in a span tag
      var text = $(this).html().split(' '),
        len = text.length,
        result = [],
        in_link = false;; 
      for( var i = 0; i < len; i++ ) {
          if (in_link) {
            result[i] = text[i];
            if (text[i].indexOf('a>')>=0) {
              in_link = false;
            }
          } else if (text[i].lastIndexOf('>')>0 && text[i].indexOf('<')<0) {
            result[i] = text[i].substring(0,text[i].indexOf('>')+1) + '<span class="todo">' + text[i].substring(text[i].indexOf('>')+1, text[i].length) + '</span>';
          } else if (text[i].lastIndexOf('>')>0 && text[i].indexOf('<')>=0) {
            console.log(text[i]);
            result[i] = text[i].substring(0,text[i].lastIndexOf('>')+1) + '<span class="todo">' + text[i].substring(text[i].lastIndexOf('>')+1, text[i].length) + '</span>';
            console.log(result[i]);
          } else if (text[i].indexOf('<')>=0) {
            result[i] = text[i];
            if (text[i].indexOf('<a')>=0) {
              in_link = true;
            }
            //result[i] = '<span class="todo">' + text[i].substring(0,text[i].indexOf('<')) + '</span>' + text[i].substring(text[i].indexOf('<'), text[i].length-1);
          } else {
            result[i] = '<span class="todo">' + text[i] + '</span>';
          }
      }
      
      $(this).html(result.join(' '));
      // 2. now read through each word
      var $candidates = [];
      $('.todo').each(function() {
        $w = $(this);
        $candidates = consider_word($candidates, $w);
        $w.removeClass('todo');
        $w.addClass('done');
      }); 
      if ($candidates.length>0 ) {
        var valid_phrase = get_phrase($candidates);
        if (valid_phrase) {
          convert_candidates_to_link($candidates, '.candidate' , valid_phrase);
        } else {
          $candidates = [];
        }
      }
    });
});
